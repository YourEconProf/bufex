def create_new_game(game_file):
    import pandas as pd
    from tkinter import filedialog
    import globalvars

    print("INITIALIZING NEW GAME: CREATE GAME FILE")
    game_file = filedialog.asksaveasfilename()
    print(game_file)
    write_logfile(game_file, "#MCRTRADING ")
    write_logfile(game_file, "LOG FILE INITIATED: " + game_file)

    # Tables:
    #	traders (contains deposits)
    #	contracts
    #	transactions	# create the tables in the database

    # import roster file
    # csv format, "Name", Badge, Code, deposit
    input("Hit any key to open the roster file")
    roster_file_name = filedialog.askopenfilename()
    roster = pd.read_csv(roster_file_name).as_matrix()
    roster = pd.DataFrame(roster, columns=[['All', 'All', 'All', 'All'], ['Name', 'Badge', 'Code', 'Deposit']],
                          index=roster[:, 1])
    roster.columns.names = ['Week', 'Data']
    if globalvars.debug > 5:
        print(roster[:5])
    roster.to_pickle(game_file + "_roster")
    write_logfile(game_file, "Loaded Roster File: " + roster_file_name + " \n")

    # create contracts
    # csv format symbol, tick, initial margin, maint marg
    input("Hit any key to open the contracts file")
    contracts_file = filedialog.askopenfilename()
    contracts = pd.read_csv(contracts_file)
    contracts.to_pickle(game_file + "_contracts")
    write_logfile(game_file, "Loaded Contracts File: " + contracts_file + " \n")
    write_logfile(game_file, "GAME INITIALIZATION COMPLETED")
    if globalvars.debug > 5:
        print(contracts)
    print("GAME INITIALIZATION COMPLETED")
    print("")

    return game_file


def import_trading_data(game_file, import_trades):
    from tkinter import filedialog
    from datetime import datetime
    import pandas as pd
    import numpy as np
    import os
    import pdb
    import globalvars

    if globalvars.debug > 5:
        print(globalvars.CLoptions)

    # pdb.set_trace()

    # ask for trading session name:
    if globalvars.CLoptions.sessionname == None:
        session_name = input("What is the session Name?")
    else:
        session_name = globalvars.CLoptions.sessionname

    if import_trades:
        # IMPORT NEW TRADES
        # BuyBadge SellBadge Qty Symbol Price Date
        if globalvars.CLoptions.trading == None:
            input("Hit any key to open the trade file")
            trade_file_name = filedialog.askopenfilename()
            transactions = pd.read_csv(trade_file_name)
        else:
            transactions = pd.read_csv(globalvars.CLoptions.trading)

        # Seperate out buys & sells, to then be combined with open positions
        # from previous sessions
        buys = transactions[['BuyBadge', 'Qty', 'Cmdty', 'Price']]
        buys = buys.rename(columns={'BuyBadge': 'Badge'})
        sells = transactions[['SellBadge', 'Qty', 'Cmdty', 'Price']]
        sells = sells.rename(columns={'SellBadge': 'Badge'})

        # CALCULATE TRADE QTYS: (FOR GRADING)
        trading_qty = trading_data(buys, sells)

        # PRINT OUT NEW TRADES (INTO CSV)
        # this file
        sells_copy = sells.copy()
        print_trades(buys, sells_copy, game_file, session_name)
        del sells_copy
        write_logfile(game_file, "Processed Trades File: " + trade_file_name + " \n")
    else:
        trading_qty = [0, 0];

    # Open Contracts File:
    contract_specs = pd.read_pickle(game_file + "_contracts")

    # bring in open positions
    if os.path.isfile(game_file + "_open_positions"):  # then there are open positions
        open_positions = pd.read_pickle(game_file + "_open_positions")
        open_buys_long = open_positions[np.isnan(open_positions['SellPrice'])]
        open_buys_long = open_buys_long.rename(columns={'BuyPrice': 'Price'})
        open_buys_long = open_buys_long[['Badge', 'Qty', 'Cmdty', 'Price']]
        open_sells_long = open_positions[np.isnan(open_positions['BuyPrice'])]
        open_sells_long = open_sells_long.rename(columns={'SellPrice': 'Price'})
        open_sells_long = open_sells_long[['Badge', 'Qty', 'Cmdty', 'Price']]
        if import_trades:
            buys = pd.concat([buys, open_buys_long])
            sells = pd.concat([sells, open_sells_long])
        else:
            buys = open_buys_long
            sells = open_sells_long

    #### PRODUCTION
    # list of traded contracts:
    # This has to go here, to handle case that open position is not traded
    # it will still need a settlement price.
    answer = "N"
    while answer == "N":
        contracts1 = pd.concat([buys, sells]).Cmdty
        contracts1 = contracts1.drop_duplicates()
        contracts = pd.DataFrame(columns=['Settle', 'Price'], index=contracts1)
        if globalvars.CLoptions.settlefile == None:
            for contract in contracts1:
                contracts['Settle'][contract] = input("Is " + contract + " settling? Y/N ")
                contracts['Price'][contract] = input("At what price is " + contract + " settling/mtm? ")
            answer = input("Are these correct? [Y/N]")
        else:
            settle_file = pd.read_csv(globalvars.CLoptions.settlefile, index_col=0, delim_whitespace=True)
            for contract in contracts1:
                contracts['Settle'][contract] = settle_file['Settle'][contract]
                contracts['Price'][contract] = settle_file['Price'][contract]
            answer = "Y"

    # Need to output 'contracts' to log file here


    # expand trades list from each row being a transaction to each row being
    # a single contract traded to facilitate trade matching
    buys_long = expand_transactions(buys)
    buys_long = buys_long.rename(columns={'Price': 'BuyPrice'})

    sells_long = expand_transactions(sells)
    sells_long = sells_long.rename(columns={'Price': 'SellPrice'})

    # join the buys_long and sells_long dataframes to see what
    # is offset in trading and the settling contracts.

    closed = pd.merge(buys_long, sells_long, on=['Badge', 'Cmdty', 'Qty'], how='outer');
    closed.index = range(len(closed.index))
    # Because something in the merge above changes the dtype of these variables??
    closed[['Badge', 'Qty', 'BuyPrice', 'SellPrice']] = closed[['Badge', 'Qty', 'BuyPrice', 'SellPrice']].astype(float)

    # open positions get carried to the next week:
    # to be an open position, you need to have a NaN from the matching process
    #   which means that you weren't offset on the day of trading
    # you also need to be one of the non-settling contracts
    #   That step occurs below, resulting in 'open_positions'
    close_settle_symbols = contracts[contracts['Settle'].apply(lambda x: 'Y' in x)].index
    closed['Settled'] = (
    closed['Cmdty'].isin(close_settle_symbols) | ~np.any(np.isnan(closed[['BuyPrice', 'SellPrice']]), 1))

    # Find open positions: positions that are neither offset nor settled
    #  and will be carried to next session
    open_positions = closed[~closed['Settled']]
    open_positions['Qty'] = 1

    # Write out these positions for inclusion next time!
    #   This file is for use by the software
    open_positions.to_pickle(game_file + "_open_positions")

    #   This file should be useful to actual account holders, but its not!
    print_open_positions(open_positions, game_file, session_name)

    ###TODO check that the qty/cmdty of the open positions all evens out
    ###     as a debug check

    ### DEBUG ONLY
    if globalvars.debug > 2:
        buys.to_csv("buys.csv")
        sells.to_csv("sells.csv")
        buys_long.to_csv("buys_long.csv")
        sells_long.to_csv("sells_long.csv")
        closed.to_csv("closed.csv")

    # in 'closed' we are going to put in the settlement/mtm price for all contracts
    PriceStrings = ['BuyPrice', 'SellPrice']

    for idx in closed.index:
        for pString in PriceStrings:
            if np.isnan(closed[pString][idx]):
                closed[pString][idx] = contracts['Price'][closed['Cmdty'][idx]]

    # pdb.set_trace()
    # Because something in the merge above changes the dtype of these variables??
    closed[['Badge', 'Qty', 'BuyPrice', 'SellPrice']] = closed[['Badge', 'Qty', 'BuyPrice', 'SellPrice']].astype(int)
    closed['Profit'] = closed['SellPrice'] - closed['BuyPrice']
    closed['Profit'] = closed['Profit'].astype(int)
    closed = pd.merge(closed, contract_specs, on=['Cmdty'])
    closed['Profit'] = closed['Profit'] * closed['Tick']

    # Find closed/settled contracts:
    close_settle = closed[closed['Settled']].copy()
    print("These are profits that are already settled/closed: " + str(close_settle['Profit'].sum()))

    # calculate profit per badge for mtm contracts:
    mtm_positions = closed[~closed['Settled']].copy()
    badge_groups = mtm_positions['Profit'].groupby(mtm_positions['Badge'])
    badge_mtm_profits = badge_groups.sum()
    print("These are M-T-M profits: " + str(badge_mtm_profits.sum()))
    print("The above two lines should sum to 0")

    # calculate profit per badge for closed/settled contracts:
    badge_groups = close_settle['Profit'].groupby(close_settle['Badge'])
    badge_settle_profits = badge_groups.sum()
    # print("This should be zero [BSP]: "+str(badge_settle_profits.sum()))

    # calculate margin deposit required by each badge
    # start with # open contracts per badge
    badge_margin = mtm_positions['InitMarg'].groupby(mtm_positions['Badge']).sum()

    if import_trades:
        output_info = {'Margin': badge_margin,
                       'ClsPrft': badge_settle_profits,
                       'MTMPrft': badge_mtm_profits,
                       'NTrades': trading_qty[0],
                       'QtyTrded': trading_qty[1]}
    else:
        output_info = {'Margin': badge_margin,
                       'ClsPrft': badge_settle_profits,
                       'MTMPrft': badge_mtm_profits}

    # create dataframe w/ new info for this week
    # add column super titles
    output_info = pd.concat({session_name: pd.DataFrame(output_info)}, axis=1)

    # Load Roster File:
    roster = pd.read_pickle(game_file + "_roster")

    # Add new information using Game Name as Upper Column Name
    new_roster = pd.merge(roster, output_info, left_index=True, right_index=True, how='left')
    new_roster = new_roster.fillna(0)

    # Settled Profit
    new_roster[session_name, 'ClsBal'] = new_roster['All', 'Deposit'] + new_roster.xs('ClsPrft', level=1, axis=1).sum(
        axis=1)
    new_roster[session_name, 'MTMBal'] = new_roster[session_name, 'ClsBal'] + new_roster[session_name, 'MTMPrft'] - \
                                         new_roster[session_name, 'Margin']

    # Save Modified Roster:
    new_roster.to_pickle(game_file + "_roster")

    # output roster:
    print_roster(new_roster, game_file, session_name)

    if globalvars.debug > 2:
        new_roster = new_roster.set_index(roster.All.Code)
        new_roster = new_roster.sort_index()
        new_roster.to_html(open(game_file + "_" + session_name + "_DEBUGROSTER.html", 'w'))


def deposit_money(game_file):
    from tkinter import filedialog
    from datetime import datetime
    import pandas as pd
    import numpy as np
    import os
    import pdb
    import globalvars

    if globalvars.debug > 5:
        print(globalvars.CLoptions)

    # pdb.set_trace()

    # ask for trading session name:
    if globalvars.CLoptions.sessionname == None:
        session_name = input("What is the session Name?")
    else:
        session_name = globalvars.CLoptions.sessionname

    trading_qty = [0, 0]

    output_info = {'Margin': badge_margin,
                       'ClsPrft': badge_settle_profits,
                       'MTMPrft': badge_mtm_profits}

    # create dataframe w/ new info for this week
    # add column super titles
    output_info = pd.concat({session_name: pd.DataFrame(output_info)}, axis=1)

    # Load Roster File:
    roster = pd.read_pickle(game_file + "_roster")

    # Add new information using Game Name as Upper Column Name
    new_roster = pd.merge(roster, output_info, left_index=True, right_index=True, how='left')
    new_roster = new_roster.fillna(0)

    # Settled Profit
    new_roster[session_name, 'ClsBal'] = new_roster['All', 'Deposit'] + new_roster.xs('ClsPrft', level=1, axis=1).sum(
        axis=1)
    new_roster[session_name, 'MTMBal'] = new_roster[session_name, 'ClsBal'] + new_roster[session_name, 'MTMPrft'] - \
                                         new_roster[session_name, 'Margin']

    # Save Modified Roster:
    new_roster.to_pickle(game_file + "_roster")

    # output roster:
    print_roster(new_roster, game_file, session_name)

    if globalvars.debug > 2:
        new_roster = new_roster.set_index(roster.All.Code)
        new_roster = new_roster.sort_index()
        new_roster.to_html(open(game_file + "_" + session_name + "_DEBUGROSTER.html", 'w'))


def expand_transactions(trans):
    import pandas as pd
    # import pdb

    trans = trans.groupby([trans['Badge'], trans['Cmdty'], trans['Price']]).sum()
    del trans['Badge']
    del trans['Price']
    trans = trans.reset_index()

    out = trans.copy()
    out = out.iloc[0:1]

    for item in trans.index:
        counter = 1
        for i in range(abs(trans['Qty'][item])):
            out = out.append(trans.ix[item], ignore_index=True)
            out['Qty'][max(out.index)] = counter
            counter = counter + 1
    # pdb.set_trace()
    out = out.ix[1:]

    counter = 1
    for idx in out.index[1:]:
        if all(out[['Badge', 'Cmdty']].iloc[idx - 1] == out[['Badge', 'Cmdty']].iloc[idx - 2]):
            counter = counter + 1
        else:
            counter = 1
        out['Qty'].iloc[idx - 1] = counter

    return out


def print_trades(buys, sells, game_file, session_name):
    import pandas as pd
    # import pdb

    sells['Qty'] = sells['Qty'] * -1
    all = pd.concat([buys, sells])

    # load roster file:
    roster = pd.read_pickle(game_file + "_roster")
    roster = roster.All[['Badge', 'Code']]
    all = pd.merge(all, roster, on='Badge')

    del all['Badge']

    all = all.sort(columns=['Code', 'Cmdty'])
    # all.to_csv(game_file+session_name+"_trading.csv",index=False,columns=['Code','Qty','Cmdty','Price'])
    all.to_html(open(game_file + "_" + session_name + "_trading.html", 'w'), index=False,
                columns=['Code', 'Qty', 'Cmdty', 'Price'])


def print_open_positions(open_positions, game_file, session_name):
    import pandas as pd
    # import pdb

    # load roster file:
    roster = pd.read_pickle(game_file + "_roster")
    roster = roster.All[['Badge', 'Code']]
    all = pd.merge(open_positions, roster, on='Badge')

    del all['Badge']

    all = all.sort(columns=['Code', 'Cmdty'])
    all.to_html(open(game_file + "_" + session_name + "_open_positions.html", 'w'), index=False,
                columns=['Code', 'Cmdty', 'BuyPrice', 'Qty', 'SellPrice'])


def print_roster(in_roster, game_file, session_name):
    import pandas as pd
    # import pdb

    roster = in_roster.copy()

    # delete names:
    del roster['All', 'Name']
    del roster['All', 'Badge']
    roster = roster.set_index(roster.All.Code)
    # pdb.set_trace()
    roster = roster.sort_index()
    roster.index = range(len(roster['All', 'Deposit']))
    # roster.to_csv(game_file+"_"+session_name+"_results.csv",index=False)
    roster.to_html(open(game_file + "_" + session_name + "_results.html", 'w'))


def write_logfile(game_file, log_text):
    import datetime

    with open(game_file, "a") as logfile:
        logfile.write("# " + datetime.datetime.now().strftime('%Y-%m-%d-%H:%M') + "\n")
        logfile.write(log_text + "\n")

    logfile.close()


def trading_data(buys, sells):
    import pandas as pd
    # import pdb
    all = pd.concat([buys, sells])

    # maybe the abs() should go here??
    all_group = all['Qty'].groupby(all['Badge'])

    trades = all_group.count()
    qty_traded = all_group.sum()

    output = [trades, qty_traded]

    return output


def print_account_statements(game_file):
    import pandas as pd
    import pdb
    import globalvars
    from math import floor as floor

    # This function prints out most recent results, with names, as well as
    # cumulative trading activity stats.

    # pdb.set_trace()

    # Open Modified Roster:
    roster = pd.read_pickle(game_file + "_roster")
    roster.to_html(open(game_file + "_PROF_FINAL.html", 'w'))


# Calculate sums across sessions:
# Trading Profits
# finals = roster.copy
# finals['All','EndBal']=roster['All','Deposit'] + roster.xs('ClsPrft',level=1,axis=1).sum(axis=1)
# finals['NTrades']=roster.xs('NTrades',level=1,axis=1).sum(axis=1)
# finals['QtyTrded']=roster.xs('QtyTrded',level=1,axis=1).sum(axis=1)
# finals['Dollars'] = floor(roster['EndBal']/100)
# finals['Quarters'] = floor((roster.EndBal - finals['Dollars']*100)/25)
# finals['Dimes'] = floor((roster.EndBal - finals['Dollars']*100 -finals['Quarters']*25)/10)
# finals['Nickels'] = floor((roster.EndBal - finals['Dollars']*100 -finals['Quarters']*25 - finals['Dimes']*10)/5)
# finals['Pennies'] = (roster.EndBal - finals['Dollars']*100 -finals['Quarters']*25 - finals['Dimes']*10 - finals['Nickels']*5)
# del finals['Deposit']

# output roster:
# finals.to_html(open(game_file+"_PROF_FINAL.html",'w'))
# del finals['Name']
# finals.to_html(open(game_file+"_STUDENT_OUT.html",'w'))

def open_game_file(game_file):
    from tkinter import filedialog

    if game_file == None:
        print("OPENING GAME: CHOOSE GAME FILE")
        game_file = filedialog.askopenfilename()
    with open(game_file, "a") as logfile:
        write_logfile(game_file, "Opening Game File: " + game_file + " \n")
    # logfile.write("Opening Game File: "+game_file+" \n")
    # logfile.closed

    return game_file
