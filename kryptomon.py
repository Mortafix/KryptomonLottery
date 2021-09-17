from argparse import ArgumentParser
from datetime import datetime
from math import floor
from re import match

from colorifix.colorifix import paint
from requests import get

API_KEY = "API_KEY"
ADDRESS = "0x50a1b4C905834291398a8dD140fa4A9AA9521f07"  # Kryptomon wallet
LOTTERIES_TIMESTAMP = [
    1631444400,
    1632049200,
    1632654000,
    1633258800,
    1633863600,
    1634468400,
    1635073200,
    1635681600,
    1636286400,
]


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
    params = {
        "module": "account",
        "action": "txlist",
        "address": ADDRESS,
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


def get_tickets_blocks(blocks):
    """Get data from transactions block"""
    params = {
        "module": "logs",
        "action": "getLogs",
        "fromBlock": blocks[-1],
        "toBlock": blocks[0],
        "topic0": "0xc3d9208034e72b3cd2d1b5f1e9911ebc02e7be185fca8924062b57bd5464afd4",
        "address": ADDRESS,
        "apikey": API_KEY,
    }
    response = get("https://api.bscscan.com/api", params=params).json().get("result")
    return {
        int(data.get("blockNumber"), 0): int(data.get("data"), 0) for data in response
    }


def lottery_overview(lottery):
    """Get unique wallets"""
    overview = dict()
    transactions = get_tickets_blocks([block for block, _ in lottery])
    for block, who in lottery:
        bet_ticket = overview.get(who, 0)
        if block in transactions:
            overview[who.lower()] = bet_ticket + transactions.get(block)
    return overview


def lottery_summary(overview, my_wallet):
    """Show current summary"""
    ticket_own = overview.get(my_wallet.lower()) if my_wallet else 0
    unique_tickets, total_ticket = list(overview.values()), sum(overview.values())
    summary = {tck: unique_tickets.count(tck) for tck in set(unique_tickets)}
    return "\n".join(
        f"> [#magenta]{players:>3}[/] wallet(s) bet [#green]{ticket:>3}[/] ticket(s)"
        f" with [#blue]{win_probability(ticket, total_ticket, len(overview)):>5.2%}[/] "
        "winning probability"
        + (" [!cyan #white] YOU [/]" if ticket == ticket_own else "")
        for ticket, players in summary.items()
    )


def win_probability(ticket_bet, total_tickets, players):
    """Calculate a probability estimation of victory"""
    eggs = floor(players / 10)
    mean_tickets_bet = total_tickets / players
    # mean estimation about total tickets burnt from other eggs
    total_less_mean = total_tickets - (eggs * mean_tickets_bet / 2)
    return 1 - ((total_less_mean - ticket_bet) / total_less_mean) ** eggs


def win_probability_new_bet(ticket_bet, total_tickets, players):
    """Same as above but with an additional bet"""
    return win_probability(ticket_bet, total_tickets + ticket_bet, players + 1)


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
    return parser


def main():
    parser = argparsing()
    args = parser.parse_args()
    print()
    if not (0 <= args.lottery <= 8):
        paint("[#red]Week MUST be between 1 and 8!\n", True)
        exit()
    week, lottery = get_transactions(args.lottery)
    message = (
        "[@underline @bold #blue]Kryptomon Lottery\n"
        f"[/]Transactions found for week [#blue @bold]{week}[/]: [#red]{len(lottery)}"
    )
    paint(message, True)
    if not lottery:
        paint(f"Week [#blue @bold]{week}[/] NOT started yet!\n", True)
        exit()
    overview = lottery_overview(lottery)
    tickets, players = sum(overview.values()), len(overview)
    paint(
        f"Found [#red]{tickets}[/] tickets bet by [#red]{players}[/] wallet(s) for "
        f"[#red]{floor(players / 10)}[/] eggs:",
        True,
    )
    paint(lottery_summary(overview, my_wallet=args.wallet), True)
    if args.ticket > 0:
        new_prob = win_probability_new_bet(args.ticket, tickets, players)
        paint(
            f"# If you bet [#green]{args.ticket}[/] ticket(s) right now, you'll have "
            f"[#blue]{new_prob:.2%}[/] winning probability",
            True,
        )
    print()


if __name__ == "__main__":
    main()
