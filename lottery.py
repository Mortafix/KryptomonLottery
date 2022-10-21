from argparse import ArgumentParser
from datetime import datetime
from math import floor

from colorifix.colorifix import ppaint
from utils.helpers import (get_json_winners, get_transactions, get_winners,
                           lottery_overview, lottery_summary, print_summary,
                           print_winners, week_from_date,
                           win_probability_new_bet, winner_summary)


# ---- Main
def argparsing():
    """args parsing for command line"""
    parser = ArgumentParser(
        prog="Kryptomon",
        description="Get victory probabilities for Kryptomon Eggs Lottery",
        usage=("kryptomon [-w week] [-y year]"),
    )
    parser.add_argument(
        "-y",
        "--year",
        type=int,
        help="year of lottery (if not specified, current)",
        default=datetime.now().year,
        metavar=("YEAR"),
    )
    parser.add_argument(
        "-w",
        "--week",
        type=int,
        help="week number (if not specified, current)",
        default=week_from_date(datetime.now()),
        metavar=("WEEK"),
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
        "--wallet",
        type=str,
        help="personal wallet address",
    )
    return parser


def main():
    parser = argparsing()
    args = parser.parse_args()
    week, year = args.week, args.year
    # verify args
    print()
    if year == 2021 and week < 38:
        ppaint("[#red]The lottery wasn't yet born!\n")
        exit()
    if week not in range(0, 53):
        ppaint(f"[#red]{week} is not a valid week!\n")
        exit()
    if year not in range(2021, 2025):
        ppaint(f"[#red]{year} is not a valid year!\n")
        exit()

    # print transactions
    lottery, lottery_num, from_date, to_date = get_transactions(week, year)
    ppaint(
        f"[@underline @bold #blue]Kryptomon Lottery Staking[/@] ({lottery_num}°)[/]\n"
        f"[#gray]# {from_date:%d.%m.%Y} -> {to_date:%d.%m.%Y}[/]\n\nTransactions "
        f"found for [#blue @bold]w{week}:{year}[/]: [#magenta]{len(lottery)}"
    )
    if not lottery:
        ppaint(f"Lottery [#blue @bold]w{week}:{year}[/] NOT started yet!\n")
        exit()

    # print overview
    overview = lottery_overview(lottery)
    tickets, players = sum(overview.values()), len(overview)
    total_eggs = floor(players / 10)
    ppaint(
        f"Found [#magenta]{tickets}[/] tickets bet by [#magenta]{players}[/] "
        f"wallet(s) for [#magenta]{total_eggs}[/] egg(s):",
    )
    own_tickets = overview.get(args.wallet.lower()) if args.wallet else 0
    summary = lottery_summary(overview, my_wallet=args.wallet)
    print_summary(overview, summary, tickets, own_tickets)

    # print tickets bet
    if args.ticket > 0:
        new_prob = win_probability_new_bet(args.ticket, tickets, players)
        ppaint(
            f"# If you bet [#green]{args.ticket}[/] ticket(s) right now, you'll have "
            f"[#blue]{new_prob:.2%}[/] winning probability",
        )

    # print winners
    json_winners = get_json_winners()
    egg_winners = get_winners(from_date, lottery_num)
    eggs_claimed = len(egg_winners)
    if egg_winners:
        ppaint("\n[@bold @underline #yellow]---- WINNERS ----[/]")
        ppaint(f"Eggs claimed: [#magenta]{eggs_claimed}[/] of [@bold]{total_eggs}[/]")
        winners_summary = winner_summary(overview, egg_winners, json_winners)
        print_winners(summary, winners_summary)
    print()


if __name__ == "__main__":
    main()
