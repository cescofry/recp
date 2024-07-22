#!/usr/bin/env python3


import curses
import curses.ascii
from doctest import debug
import subprocess
import os
import sys
import json
from typing import OrderedDict
from xml.etree.ElementTree import VERSION


# EXPORT BIN TO PATH:
# export PATH=$PATH:$HOME/Library/Mobile\ Documents/com\~apple\~CloudDocs/bin:$PATH


TITLE = "ReCP"
CONFIG_FILE_NAME = ".recp"
ESC_KEY = 27
VERSION = "0.1.2"

# Styles
BACKGROUND_COLOR = curses.COLOR_BLACK
DEFAULT_STYLE = (curses.COLOR_WHITE, BACKGROUND_COLOR)
ERROR_STYLE = (curses.COLOR_RED, BACKGROUND_COLOR)
SELECTED_STYLE = (curses.COLOR_BLACK, curses.COLOR_WHITE)
ACCENT_STYLE = (curses.COLOR_GREEN, BACKGROUND_COLOR)



#
# ReCP Main class
#
class ReCP:
    def __init__(self, config, isDebugEnabled = False):
        self.config = config
        self.recipes = []
        self.history = []
        self.isDebugEnabled = isDebugEnabled

        log(f"Loading {len(self.recipes)} recipes")

        
        self.inputMode = 0 # 0: Actions and Browse, 1: Search
        self.userInput = "" #Activated by / deactivated by ESC
        self.option = -1
        self.isInRecipeMode = True
        self.shouldHideOtherMode = False
        self.shouldShowInfo = False
        self.shouldQuit = False
        self.commandToExecute = None
        self.debug = f"Version: {VERSION}"
        
        os.environ.setdefault('ESCDELAY', '25') # Reduce the delay for the ESC key to be recognized
        
    
    def setupDisplayConfiguration(self):
        curses.start_color()
        curses.init_pair(1, DEFAULT_STYLE[0], DEFAULT_STYLE[1])
        curses.init_pair(2, ERROR_STYLE[0], ERROR_STYLE[1]) # Error
        curses.init_pair(3, SELECTED_STYLE[0], SELECTED_STYLE[1]) # Selected
        curses.init_pair(4, ACCENT_STYLE[0], ACCENT_STYLE[1]) # Accent
        curses.curs_set(2) 

        
    # define the runloop
    def runloop(self):
        
        # define the curses wrapper
        def character(stdscr):
            stdscr.scrollok(1)

            while self.shouldExit() == False:
                self.draw(stdscr)
                self.handleUserInput(stdscr)
                
            # clean screen before exiting
            stdscr.clear()
            

        # Call the character function
        curses.wrapper(character)
        self.execCommandIfAvailable()

    
    # Draw all the elements of the screen (Title, options, StatusBar)
    def draw(self, stdscr):
        self.setupDisplayConfiguration()
        
        stdscr.erase()
        stdscr.refresh()

        # Setup measurements
        height, width = stdscr.getmaxyx()

        statusY = height - 1
        # Show Recipes Only
        if self.shouldHideOtherMode:
            sectionH = height - 2
            recipesY = 1
            width = width - 2

            # Draw onle th ecurrent selected mode
            if self.isInRecipeMode:
                self.drawRecipes(recipesY, width, sectionH)
            else:
                self.drawHistory(recipesY, width, sectionH)
        else:
            sectionH = int((height - 2) / 2)
            recipesY = 1
            historyY = recipesY + sectionH
            width = width - 2

            # add the Reciped
            self.drawRecipes(recipesY, width, sectionH)

            # add the History
            self.drawHistory(historyY, width, sectionH)
                
        # Add the StatusBar
        self.drawStatusBar(stdscr, statusY, width)
        
        #Debug
        self.drawDebug(stdscr)
        
    
    def drawRecipes(self, y, width, height):
        tuples = list(map(lambda x: (x, f"{x['title']} {x['recipe']}"), self.config.recipes))
        self.recipes = self.filteredItems(tuples, height)
        
        title = "Recipes" 
        if self.shouldShowInfo:
            title = f"{title}   -> {self.config.source}"
            
        style = 4 if self.isInRecipeMode else 1
        window = self.getWindow(title, 1, y, width, height, style)
        if len(self.recipes) == 0:
            window.addstr("No Recipe found. Choose from History")

        for i in range(len(self.recipes)):
            recipe = self.recipes[i]
            recipeStr = f"[{i}] {recipe['title']}"

            style = 3 if self.isInRecipeMode and i == self.option else 1
            window.addstr(recipeStr, curses.color_pair(style))
            
            if self.shouldShowInfo:
                # Limit the recipe string to the width of the screen
                infoStr = stringLimitedToWidth(f"\t# {recipe['recipe'].strip()}", width, recipeStr)
                window.addstr(infoStr, curses.color_pair(4))
            if i < len(self.recipes) -1:
                window.addstr('\n')
        window.refresh()
       

    def drawHistory(self, y, width, height):
        tuples = list(map(lambda x: (x, x), self.getHistory()))
        self.history = self.filteredItems(tuples, height)
        
        style = 4 if self.isInRecipeMode == False else 1
        window = self.getWindow("History", 1, y, width, height, style)
        if len(self.history) == 0:
            window.addstr("No History found !!!")

        for i in range(len(self.history)):
            line = self.history[i]
            lineStr = stringLimitedToWidth(f"[{i}] {line.strip()}", width)
            style = 3 if self.isInRecipeMode == False and i == self.option else 1
            window.addstr(lineStr, curses.color_pair(style))
            if i < len(self.history) -1:
                window.addstr('\n')

        window.refresh()
        
        
    def drawDebug(self, stdscr):
        if self.isDebugEnabled == False or len(self.debug) == 0:
            return
        
        height, width = stdscr.getmaxyx()
        windW = width - 10
        windH = 4
        x = int((width - windW) / 2)
        y = int((height - windH) / 2)
        win = self.getWindow("Debug", x, y, windW, windH, 4)
        
        win.clear()
        win.addstr(f"{self.debug}")
        win.refresh()
        
    #
    # Status Bar
    #
       
    # KEybindings to be used to trigger actions and draw statusbar
    keyBinding = { 
        'Q' : "[Q]uit",
        '+' : "[+]Info",
        'H' : "[H]ide",
        'S' : "[S]ave",
        'D' : "[D]elete",
        'C' : "[C]opy",
        '/' : "[/]Search"
    }
    
    def isCharacterKey(self, input, expected): 
        if self.inputMode == 1:
            return False
        else:
            return chr(input).upper() == expected.upper()
       
    def drawStatusBar(self, stdscr, y, width):
        height, width = stdscr.getmaxyx()
        
        def keyBindingString(key, isActive):
            if isActive == False:
                return ""
            
            return self.keyBinding[key] 
        
        # Searchinb mode
        if self.inputMode == 1:
            items = [
                "[Tab]Switch",
                "[Enter]Run Selected" if self.option >= 0 else "",
                "[ESC]Actions",
                f" Search: {self.userInput}"
            ]
        # Action mode
        else:
            items = [
                keyBindingString('Q', True),
                keyBindingString('+', True),
                "[Tab]Switch",
                "[H]hide" if self.shouldHideOtherMode else "[H]Show",
                "[Enter]Run Selected" if self.option >= 0 else "",
                keyBindingString('S', self.option >= 0 and self.isInRecipeMode == False),
                keyBindingString('D', self.option >= 0 and self.isInRecipeMode),
                keyBindingString('C', self.option >= 0),
                f"[/]Search: {self.userInput}"
            ]
        
        statusBar = "   ".join(filter(lambda item: len(item) > 0, items))
            
        stdscr.attron(curses.color_pair(3))
        stdscr.addstr(y, 0, statusBar)
        spaceLeft = width - len(statusBar) - 1
        if spaceLeft > 0:
            stdscr.addstr(y, len(statusBar), " " * spaceLeft)
            if self.inputMode == 1:
                stdscr.move(y, len(statusBar))
        stdscr.attroff(curses.color_pair(3))      
        
        

    # Get the option from the user input. Arrows move the current selection
    def handleUserInput(self, stdscr):
        c = stdscr.getch()
        currentCharacter = chr(c)

        items = self.history if self.isInRecipeMode == False else list(map(lambda x: x['recipe'], self.recipes))
        otherItems = self.history if self.isInRecipeMode else list(map(lambda x: x['recipe'], self.recipes))
        
        # handle the arrow keys
        if c == curses.KEY_UP:
            self.option -= 1
            if self.option < 0:
                if len(otherItems) > 0 and self.shouldHideOtherMode == False:
                    self.isInRecipeMode = not self.isInRecipeMode
                    self.option = len(otherItems) - 1
                else:
                    self.option = len(items) - 1
        elif c == curses.KEY_DOWN:
            self.option += 1
            if self.option > len(items) -1:
                if len(otherItems) > 0 and self.shouldHideOtherMode == False:
                    self.isInRecipeMode = not self.isInRecipeMode
                    self.option = 0
                else:
                    self.option = 0         
                
        # Handle the Tab key
        elif currentCharacter == '\t':
            self.option = 0
            self.isInRecipeMode = not self.isInRecipeMode
        # Handle Enter key
        elif c == 10:
            self.queueCommandForExecution(items, self.option)
        # Handle Search
        elif self.isCharacterKey(c, '/'):
            self.inputMode = 0 if self.inputMode == 1 else 1
            self.userInput = ""
        elif c == ESC_KEY:
            self.inputMode = 0 if self.inputMode == 1 else 1
         # Handle action mode
        elif self.isCharacterKey(c, 'Q'):
            self.shouldQuit = True
        elif self.isCharacterKey(c, '+'):
            self.shouldShowInfo = not self.shouldShowInfo
        elif self.isCharacterKey(c, 'S'):
            self.addCommandToRecipes(stdscr, items, self.option)
        elif self.isCharacterKey(c, 'D'):
            self.deleteCommandFromRecipes(stdscr, items, self.option)
        elif self.isCharacterKey(c, 'C'):
            self.queueCommandForCopy(items, self.option)
        elif self.isCharacterKey(c, 'H'):
            self.shouldHideOtherMode = not self.shouldHideOtherMode
            
        elif c == curses.KEY_BACKSPACE or c == 127:
            if len(self.userInput) > 0:
                self.userInput = self.userInput[:-1]
        else:
            if self.inputMode == 1:
                self.userInput = f"{self.userInput}{chr(c)}" 
                # self.debug = f"{c} : {chr(c).lower()}"

        


    # Intents

    def shouldExit(self):
        return self.shouldQuit or self.commandToExecute is not None
    

    def queueCommandForExecution(self, items, option):
        if option >= 0 and option < len(items):
            self.commandToExecute = items[option]
            
    def queueCommandForCopy(self, items, option):
        if option >= 0 and option < len(items):
            self.commandToExecute = f"echo ' {items[option].strip()} ' | pbcopy"
    
    def addCommandToRecipes(self, stdscr, items, option):
        if self.isInRecipeMode == False and option >= 0 and option < len(items):
            self.addRecipe(stdscr, items[option])
            
    def deleteCommandFromRecipes(self, stdscr, items, option):
        if self.isInRecipeMode and option >= 0 and option < len(items):
            self.deleteRecipe(stdscr, items[option])
    
    


    def filteredItems(self, itemsSearchTuples, height):
        if len(self.userInput) > 0:
            filtered = list(filter(lambda tuple: self.userInput in tuple[1], itemsSearchTuples))
            filteredStrings = list(map(lambda x: x[0], filtered))
            return listLimitedToHeight(filteredStrings, limit=height-2)
        
        else:
            filteredStrings = list(map(lambda x: x[0], itemsSearchTuples))
            return listLimitedToHeight(filteredStrings, limit=height-2)
        
    
    def getWindow(self, title, x, y, width, height, style = 1):
        box = curses.newwin(height, width, y, x) # height, width, y, x
        box.box()
        box.addstr(0, 3, title, curses.color_pair(style))
        box.refresh()

        window = curses.newwin(height-2, width-2, y+1, x+1)
        window.refresh()

        return window

    #
    # Add Recipe
    #

    def addRecipe(self, stdscr, recipe):
        height, width = stdscr.getmaxyx()
        windW = 40
        windH = 4
        x = int((width - windW) / 2)
        y = int((height - windH) / 2)
        win = self.getWindow("Recipe Name", x, y, windW, windH, 4)
        
        input = ""
        while True:
            win.clear()
            win.addstr(f"{input}")
            win.refresh()
            
            c = stdscr.getch()
            if c == curses.KEY_BACKSPACE or c == 127:
                if len(input) > 0:
                    input = input[:-1]
            elif c == ESC_KEY:
                return
            elif c == 10 and len(input) > 1: # Enter key
                # Save the recipe
                value = {
                    'recipe': recipe,
                    'title': input.strip()
                }
                   
                allRecipes = self.config.recipes 
                allRecipes.append(value)
                self.config.recipes = allRecipes
                self.config.save()
                self.option = -1
                
                self.debug = f"RECIPE ADDED: {len(allRecipes)} | {len(self.config.recipes)}"
                
                return
            else:
                input = f"{input}{chr(c)}" 


    def deleteRecipe(self, stdscr, recipe):

        height, width = stdscr.getmaxyx()
        windW = 100
        windH = 4
        x = int((width - windW) / 2)
        y = int((height - windH) / 2)
        win = self.getWindow("Delete", x, y, windW, windH, 4)
        
        
        win.clear()
        recipeS = stringLimitedToWidth(f"Recipe: {recipe.strip()}", windW)
        win.addstr(recipeS)
        win.addstr(f"\nAre you sure you want to delete? [y]es/[N]o")
        win.refresh()
        
        while True:
            
            
            c = stdscr.getch()
            cs = chr(c).lower()
            if cs == 'y':
                self.config.recipes = list(filter(lambda x: x['recipe'] != recipe, self.config.recipes))
                self.config.save()
                self.option = -1
                
                self.debug = f"RECIPE REMOVED: {len(self.config.recipes)}"
                
                return
            elif cs == 'n' or c == ESC_KEY:
                return


    def getHistory(self): # TODO: REMOVE
        # get list of recent executed commands
        recent = subprocess.run("fc -l -250 | cut -c 8-", shell = True, capture_output = True, text = True)
        
        shell_map = { "/bin/zsh" : ".zsh_history", "/bin/bash" : ".bash_history" }
        shell = os.environ["SHELL"]

        fullPath = os.path.join(os.environ["HOME"], shell_map[shell])
        with open(fullPath, 'r', encoding='utf-8', errors='replace') as file:
            history = file.readlines()
        
        history.reverse()
        # prepend recent history to history
        history = recent.stdout.split("\n") + history

        # remove duplicates and keep the order intact
        uniqueHistory = []
        [uniqueHistory.append(x) for x in history if x not in uniqueHistory]
        return uniqueHistory
 
    def execCommandIfAvailable(self):
        
        if self.commandToExecute == None:
            return
        
        command = self.commandToExecute
        self.commandToExecute = None
        self.c = -1

        log(command)
        subprocess.run(command, shell = True)
        
    

#
# Config
#

class Config:
    def __init__(self):
        dictionary = self.getConfig()

        if 'recipes' not in dictionary:
            self.setup()
            return

        self.recipes = dictionary['recipes']
        self.source = dictionary['source']

    def getConfig(self):
        filePath = self.getFilePath()
        if filePath is None:
            return { }
        
        file = open(filePath, 'r')
        jsonStr = file.read()
        name = file.name
        if jsonStr == "":
            # there is a file, but it is not initialized.
            log(f"Initializing empty config file: {name}")
            config = { "recipes": [], "source": "" }
        else:
            print(f"Found config file: {name}")
            config = json.loads(jsonStr)
            
        if 'recipes' in config:
            config['source'] = file.name
        return config

    def providedConfigPath(self):
        filteredArgs = list(filter(lambda x: (x not in ['--debug']), sys.argv))
        if len(filteredArgs) > 1:
            return filteredArgs[-1]
        return None
    
    def getFilePath(self):
        filePath = self.providedConfigPath()
        
        if filePath is not None and os.path.isfile(filePath):
            # try to use the provided config file
            return filePath
        else:
            # check if there is a .repc file at the calling site or any parent directories
            currentPath = os.getcwd()
            while currentPath != "/":
                if os.path.isfile(os.path.join(currentPath, CONFIG_FILE_NAME)):
                    return os.path.join(currentPath, CONFIG_FILE_NAME)
                currentPath = currentPath[:currentPath.rfind('/')]
            
            # check if there is one at user path
            userConfig = os.path.join(os.path.expanduser('~'), CONFIG_FILE_NAME)
            if os.path.isfile(userConfig):
                return userConfig
            else:
                return None

    def setup(self):
        filePath = self.providedConfigPath()
        if filePath is None:
            filePath = os.path.join(os.path.expanduser('~'), CONFIG_FILE_NAME)
        
        val = input(f"\nNo RePC file found. Do you want to create one at ({filePath}) ? [Y]es, [n]o: ")
        if val == 'n':
            exit(0)

        self.recipes = []
        self.source = filePath
        self.save()

    def save(self):
        dict = {
            'recipes': self.recipes
        }
        with open(self.source, 'w') as fp:
            json.dump(dict, fp)


#
# Helper functions
# 

def log(str):
    print(str)
    

def helpIfNeeded():
    if ("--help" in sys.argv):
        print("ReCP is utility that allows to compile a list of tty commands that can then be selected using the up and down keys or the assigned shortcut binding.")
        print("The tool looks for a .recp file at the calling directory, if none is found it will recurse the path backwards until one is found. If no .recp file is found in the path the tool looks for one in the user home space. Alternatively, a path to a .recp file can be provided as an argument. ")
        print("use the --debug flag to see debug information on screen")
        exit(0)

def stringLimitedToWidth(input, width, paddingString = ""):
    paddingString.replace("\t", "    ")
    replacedInput = input.replace("\t", "    ")
    
    wLimit = min((width - len(paddingString) - 3), len(replacedInput)) # I don't know why I need to subtract 3, but it overflows otherwise. It might be the padding
    return input[0:wLimit]

def listLimitedToHeight(list, limit):
    limit = min(len(list), limit) # If the list goes off screen it will crash
    return list[0: limit]

def incrementWithLimit(value : int, limit: int):
    value += 1
    if value > limit:
        value = 0
    return value


#
# Main
#

if __name__ == '__main__':

    helpIfNeeded()

    # Add current path to execute recipe at the right level
    sys.path.append(os.getcwd())

    config = Config()

    isDebugEnabled = "--debug" in sys.argv
    recp = ReCP(config, isDebugEnabled)
    recp.runloop()
