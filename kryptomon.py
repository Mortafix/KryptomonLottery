from argparse import ArgumentParser
from datetime import datetime
from json import load
from math import floor
from os.path import exists
from re import match

from colorifix.colorifix import paint
from requests import get

API_KEY = "API_KEY"
ADDRESS_V1 = "0x50a1b4C905834291398a8dD140fa4A9AA9521f07"  # Kryptomon wallet V1
ADDRESS_V2 = "0xD3Be5e040e7a43588A679eFD0Ba4d416b11dFb40"  # Kryptomon wallet V2
ADDRESS_V3 = "0xC43CA243d562939aF0778f06246B17efc97D3B5e"  # kryptomon wallet V3
NFT_ADDRESS = "0x7a16658f04c32d2df40726e3028b600d585d99a5"  # Kryptomon NFT wallet
LOTTERIES_TIMESTAMP = [
    1631444400,  # staking V1
    1632124800,  # staking V2
    1632729600,
    1633334400,
    1633939200,
    1634544000,
    1635148800,
    1635757200,
    1636362000,
    1636981200,  # staking V3
    1637586000,
    1638190800,
]

# ---- Info lottery API


def is_right_lottery(block_timestamp, week):
    """Check if a block is in the correct lottery"""
    return LOTTERIES_TIMESTAMP[week - 1] <= block_timestamp <= LOTTERIES_TIMESTAMP[week]


def get_transactions(week):
    """Get all last kryptomon transactions"""
    if not week:
        now = datetime.timestamp(datetime.now())
        week = max(
            [i for i, time in enumerate(LOTTERIES_TIMESTAMP, 1) if now - time > 0]
        )
    address = (week == 1 and ADDRESS_V1) or (week <= 8 and ADDRESS_V2) or ADDRESS_V3
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "sort": "desc",
        "apikey": API_KEY,
    }
    response = get("https://api.bscscan.com/api", params=params).json().get("result")
    if isinstance(response, str):
        paint(f"[#white]Ops, something went wrong!\n[#red]{response}\n", True)
        exit()
    lottery = [
        (int(data.get("blockNumber")), data.get("from"))
        for data in response
        if match("0x3fd43098", data.get("input"))
        and is_right_lottery(int(data.get("timeStamp"), 0), week)
    ]
    return week, lottery


def get_tickets_blocks(blocks, week):
    """Get data from transactions block"""
    address = (week == 1 and ADDRESS_V1) or (week <= 8 and ADDRESS_V2) or ADDRESS_V3
    params = {
        "module": "logs",
        "action": "getLogs",
        "fromBlock": blocks[-1],
        "toBlock": blocks[0],
        "topic0": "0xc3d9208034e72b3cd2d1b5f1e9911ebc02e7be185fca8924062b57bd5464afd4",
        "address": address,
        "apikey": API_KEY,
    }
    response = get("https://api.bscscan.com/api", params=params).json().get("result")
    return {
        int(data.get("blockNumber"), 0): int(data.get("data"), 0) for data in response
    }


def get_winners(lottery):
    """Get winner from transactions"""
    params = {
        "module": "logs",
        "action": "getLogs",
        "topic0": "0xb94bf7f9302edf52a596286915a69b4b0685574cffdedd0712e3c62f2550f0ba",
        "address": NFT_ADDRESS,
        "apikey": API_KEY,
    }
    response = get("https://api.bscscan.com/api", params=params).json().get("result")
    return {
        "0x" + data.get("data")[-104:-64]: int(data.get("data")[-64:])
        for data in response
        if int(data.get("data")[2:66], 16) == lottery - 1
    }


# ---- Overview


def lottery_overview(lottery, week):
    """Get unique wallets"""
    overview = dict()
    transactions = get_tickets_blocks([block for block, _ in lottery], week)
    for block, who in lottery:
        bet_ticket = overview.get(who, 0)
        if block in transactions:
            overview[who.lower()] = bet_ticket + transactions.get(block)
    return overview


def lottery_summary(overview, my_wallet):
    """Show current summary"""
    # ticket_own = overview.get(my_wallet.lower()) if my_wallet else 0
    unique_tickets = list(overview.values())
    summary = {tck: unique_tickets.count(tck) for tck in sorted(set(unique_tickets))}
    return summary


def winner_summary(overview, winners, json_winners):
    wallets_win = [
        (tickets, winners.get(wallet) or json_winners.get(wallet))
        for wallet, tickets in overview.items()
        if wallet in winners or wallet in json_winners
    ]
    winners_by_tickets = dict()
    for tickets, generation in sorted(wallets_win):
        if tickets not in winners_by_tickets:
            winners_by_tickets[tickets] = [generation]
        else:
            winners_by_tickets[tickets] += [generation]
    return winners_by_tickets


# ---- JSON winners


def get_json_winners():
    if not exists("winners.json"):
        return dict()
    winners = load(open("winners.json", "rb")).get("claims")
    return {
        key.lower(): int(winners.get(key).get("generation"), 16)
        for key in winners.keys()
    }


# ---- Probability


def win_probability(ticket_bet, total_tickets, players):
    """Calculate a probability estimation of victory"""
    eggs = floor(players / 10)
    mean_tickets_bet = (total_tickets - ticket_bet) / (players - 1)
    # mean estimation about total tickets burnt from other eggs
    total_less_mean = total_tickets - (eggs * mean_tickets_bet / 2)
    return 1 - ((total_less_mean - ticket_bet) / total_less_mean) ** eggs


def win_probability_new_bet(ticket_bet, total_tickets, players):
    """Same as above but with an additional bet"""
    return win_probability(ticket_bet, total_tickets + ticket_bet, players + 1)


# ---- Pretty printing


def print_summary(overview, summary, total_ticket, ticket_own):
    string = "\n".join(
        f"> [#magenta]{players:>3}[/] wallet(s) bet [#green]{ticket:>3}[/] ticket(s) "
        f"with [#blue]{win_probability(ticket, total_ticket, len(overview)):>6.2%}[/] "
        "winning probability"
        + (" [!cyan #white] YOU [/]" if ticket == ticket_own else "")
        for ticket, players in summary.items()
    )
    paint(string, True)


def print_winners(summary, winners):
    string = "\n".join(
        f"> [#magenta]{len(generations):>3}[/] wallet(s) of [@bold]"
        f"{summary.get(tickets):>3}[/] with [#green]{tickets:>3}[/] "
        f"ticket(s) won an egg! [Gen {', '.join(map(str,generations))}]"
        for tickets, generations in winners.items()
    )
    paint(string, True)


# ---- Main
def argparsing():
    """args parsing for command line"""
    parser = ArgumentParser(
        prog="Kryptomon",
        description="Get victory probabilities for Kryptomon Eggs Lottery",
        usage=("kryptomon [-l lottery] [-t ticket_to_bet]"),
    )
    parser.add_argument(
        "-l",
        "--lottery",
        type=int,
        help="number of lottery week (if not specified, current lottery)",
        default=0,
        metavar=("LOTTERY"),
    )
    parser.add_argument(
        "-t",
        "--ticket",
        type=int,
        help="number of ticket to bet",
        default=0,
        metavar=("TICKETS"),
    )
    parser.add_argument(
        "-w",
        "--wallet",
        type=str,
        help="personal wallet address",
        metavar=("WALLET"),
    )
    parser.add_argument(
        "-v",
        "--version",
        type=int,
        default=3,
        help="version staking (v2 or v3)",
        metavar=("VERSION"),
    )
    return parser


def main():
    parser = argparsing()
    args = parser.parse_args()
    version = args.version
    print()
    if version not in (2, 3):
        paint("[#red]Staking version MUST be 2 or 3!\n", True)
        exit()
    if (version == 2 and not (0 <= args.lottery <= 8)) or not (0 <= args.lottery <= 3):
        if version == 2:
            paint("[#red]Week MUST be between 1 and 8 (Staking V2)!\n", True)
        else:
            paint("[#red]Week MUST be between 1 and 3 (Staking V3)!\n", True)
        exit()

    # print transactions
    week, lottery = get_transactions(args.lottery)
    real_week = version == 2 and week or week - 8
    message = (
        f"[@underline @bold #blue]Kryptomon Lottery (Staking V{version})\n"
        f"[/]Transactions found for week [#blue @bold]{real_week}[/]: [#red]{len(lottery)}"
    )
    paint(message, True)
    if not lottery:
        paint(f"Week [#blue @bold]{real_week}[/] NOT started yet!\n", True)
        exit()

    # print overview
    overview = lottery_overview(lottery, week)
    tickets, players = sum(overview.values()), len(overview)
    total_eggs = floor(players / 10)
    paint(
        f"Found [#red]{tickets}[/] tickets bet by [#red]{players}[/] wallet(s) for "
        f"[#red]{total_eggs}[/] eggs:",
        True,
    )
    own_tickets = overview.get(args.wallet.lower()) if args.wallet else 0
    summary = lottery_summary(overview, my_wallet=args.wallet)
    print_summary(overview, summary, tickets, own_tickets)

    # print tickets bet
    if args.ticket > 0:
        new_prob = win_probability_new_bet(args.ticket, tickets, players)
        paint(
            f"# If you bet [#green]{args.ticket}[/] ticket(s) right now, you'll have "
            f"[#blue]{new_prob:.2%}[/] winning probability",
            True,
        )

    # print winners
    json_winners = get_json_winners()
    egg_winners = get_winners(week)
    eggs_claimed = len(egg_winners)
    if egg_winners:
        paint(
            f"\n---- [@bold @underline]Week [#blue]{real_week}[/#] WINNERS[/] ----",
            True,
        )
        paint(f"Eggs claimed: [#red]{eggs_claimed}[/] of [@bold]{total_eggs}[/]", True)
        winners_summary = winner_summary(overview, egg_winners, json_winners)
        print_winners(summary, winners_summary)
    print()


if __name__ == "__main__":
    main()
