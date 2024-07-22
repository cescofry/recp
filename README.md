# ReCP

ReCP, pronounced `/ˈres.ə.pi/` is a CLI tool for Linux and MacOS that allows to search and store recent terminal commands to be used when needed.

## Config

ReCP uses `.recp` configuration files to store saved commands.
The tool looks for a `.recp` file in the current working directory and every parent directory un until `/`. If none is found it will look for one in the user space `~/.recp`
Alternatively a `.recp` file can be provided at lauch as last argument


## Install

Open your terminal and paste this command

```bash
curl -fsSL https://raw.githubusercontent.com/cescofry/recp/main/install | sh
```


## Usage

Once opened, ReCP will show a split screen with a list of the user saved commands on top (as found in the .recp config file) and a list of commands from the user history at the bottom.

* Use the `UP` and `DOWN` keys to navigate the list of commands.
* Once a command is highlighted it could be run by just hitting `Enter` or copied with `C`.
* `Tab` allows to switch between the Saved and History pane.
* `H` hides and shows the non selected pane.
* `Q` quits the program.
* `S` Saves the highlighted command to the Saved pane. Only works when a History command is highlighted
* `D` Delete the highlighted command from the Saved pane. Only works when a Saved command is highlighted
* '/' start the search function. Type any text to filter both the Saved and History pane.

> \[!WARNING\]
> All the actions activated by a letter (`Q`, `+`, `H`, etc.) are not working while in search mode, because they are part of the search text.


## 





<https://raw.githubusercontent.com/cescofry/recp/main/recp.py>
