#!/usr/bin/env python3


# To Do List:
# 1) Make sure that the game file is *actually* the game file when it is opened
# 2) Check for empty records at end of trade, roster & contract files
#    Line 339 fail in _subs occurs when there are empty rows in roster.csv

import sys
import BUFEX_subs as sub
import argparse
import globalvars

parser = argparse.ArgumentParser(description='Process CL Options, if any.')
parser.add_argument("-D", "--DEBUG", action="store", dest="debug", type=int, default=0, help="Sets Debugging Level")
parser.add_argument("-F", "--FILE", action="store", dest="commandfile", help="Command Script File")
parser.add_argument("-M", "--MASTER", action="store", dest="masterfile", help="Master Game File")
parser.add_argument("-A", "--ACTION", action="store", dest="action", help="Action to Execute")
parser.add_argument("-N", "--NAME", action="store", dest="sessionname", help="Trading Session Name")
parser.add_argument("-T", "--TRADING", action="store", dest="trading", help="Trading File Name")
parser.add_argument("-S", "--SETTLEMENT", action="store", dest="settlefile", help="Settlement File Name")

globalvars.CLoptions = parser.parse_args()
globalvars.debug = globalvars.CLoptions.debug

if globalvars.debug > 3:
    print(globalvars.CLoptions)
    print(globalvars.debug)

main_action = "Z"
game_file = None

while main_action != "E":

    if globalvars.CLoptions.commandfile is not None:
        # There is a command file present, so process it
        print(" HI MOM! ")
    elif globalvars.CLoptions.action is not None:
        # There is a command given, so do it
        main_action = globalvars.CLoptions.action
    else:

        # Interactive only
        print("Do you want to")
        print(" [C]reate new game")
        print(" [D]eposit Money In Account** ")
        print(" [P]rint Account Statements ")
        print(" [S]ettle Trades Only")
        print(" [T]rade Data Import ")
        print(" [E]xit ")
        main_action = input("Choose Action: ")

    if globalvars.CLoptions.masterfile != None:
        # A master game file is specified
        game_file = globalvars.CLoptions.masterfile

    print("MAIN_ACTION: %s " % main_action)

    if main_action == "C":
        sub.create_new_game(game_file)
    elif main_action == "P":
        game_file = sub.open_game_file(game_file)
        sub.print_account_statements(game_file)
    elif (main_action == "T" or main_action == "S"):
        if game_file == None:
            game_file = sub.open_game_file(game_file)
        ##### Check here to make sure that first line of 'game file' is what it
        ##### should be to prevent choosing wrong file.
        sub.import_trading_data(game_file, main_action == "T")
    elif main_action == "D":
        print("DEPOSIT MONEY IN ACCOUNT CODE (NOT IMPLEMENTED)")
    elif main_action == "E":
        continue
    else:
        print("oops")
        print(main_action)

    if globalvars.CLoptions.action != None:
        main_action = "E"

print("NOW EXITING BUFEX ACCOUNTING")
