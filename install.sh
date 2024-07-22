#!/bin/sh

RC='\033[0m'
RED='\033[0;31m'

SOURCE="https://raw.githubusercontent.com/cescofry/recp/main/recp.py"

DESTINATION="/usr/local/bin/"

check() {
    local exit_code=$1
    local message=$2

    if [ $exit_code -ne 0 ]; then
        echo -e "${RED}ERROR: $message${RC}"
        exit 1
    fi
}


TMPFILE=$(mktemp)
check $? "Creating the temporary file"

curl -fsL $SOURCE -o $TMPFILE
check $? "Downloading ReCP"


echo "Where do you want to install RecP (default $DESTINATION): "
read ALTDESTINATION

# check if the user has provided an alternative destination and if so assign it to DESTINATION
if [ ! -z "$ALTDESTINATION" ]; then
    DESTINATION=$ALTDESTINATION
fi

echo "sudo privilege may be required to move ReCP to $DESTINATION"

DESTINATION=$DESTINATION/recp
sudo mv $TMPFILE $DESTINATION
check $? "Moving ReCP"

chmod +x $DESTINATION
check $? "Making ReCP executable"

rm -f $TMPFILE
check $? "Deleting the temporary file"

echo "ReCP installed successfully. Restart your terminal and type recp to begin"
