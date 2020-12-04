# How to run ISerenissimi.py
The player and all the related files can be found in the pytablut folder.
In order to run a player that communicates with the Java server, run these commands from the console:

Black:
```
python3 ISerenissimi.py black 60 localhost
```
White:
```
python3 ISerenissimi.py white 60 localhost
```
First parameter is the color of the player, second parameter the time given in order to choose the move (the server timeout), third parameter the ip address of the server

# TablutCompetition
Software for the Tablut Students Competition

## Installation on Ubuntu/Debian 

From console, run these commands to install JDK 8 e ANT:

```
sudo apt update
sudo apt install openjdk-8-jdk -y
sudo apt install ant -y
```

Now, clone the project repository:

```
git clone https://github.com/AGalassi/TablutCompetition.git
```

## Run the Server without Eclipse

The easiest way is to utilize the ANT configuration script from console.
Go into the project folder (the folder with the `build.xml` file):
```
cd TablutCompetition/Tablut
```

Compile the project:

```
ant clean
ant compile
```

The compiled project is in  the `build` folder.
Run the server with:

```
ant server
```

Check the behaviour using the random players in two different console windows:

```
ant randomwhite

ant randomblack
```

At this point, a window with the game state should appear.

To be able to run other classes, change the `build.xml` file and re-compile everything
