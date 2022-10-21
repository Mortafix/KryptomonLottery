from datetime import datetime, timedelta
from json import load
from math import floor
from os.path import exists

from colorifix.colorifix import ppaint
from requests import get

API_KEY = "W7T86S5W1EMKD4CGNPIU6QKSAUFQS5TADX"
STARTING_DATE = datetime(2021, 9, 20)
STARTING_BLOCK = 11089283
TICKET_ADDRESS = "0x7a16658f04c32d2df40726e3028b600d585d99a5"

# ---- Dates


def week_from_date(date):
    return int(f"{date:%W}")


def range_from_week(week, year):
    curr_date = datetime(year, 1, 1, 11) + timedelta(days=7 * week)
    monday = curr_date - timedelta(days=curr_date.weekday())
    return monday, monday + timedelta(days=7)


def date_to_block(date):
    return (date - STARTING_DATE).days * 27_000 + STARTING_BLOCK


def lottery_number(date):
    return (date - STARTING_DATE).days // 7 + 1


# ---- Blockchain


def get_transactions(week, year):
    """Get all last kryptomon transactions"""
    from_date, to_date = range_from_week(week, year)
    params = {
        "module": "logs",
        "action": "getLogs",
        "address": TICKET_ADDRESS,
        "topic0": "0xf95ea53798af20941d63a3b7bb0a39c13c7efcfcf84ee335781630f80036890d",
        "fromBlock": date_to_block(from_date),
        "apikey": API_KEY,
    }
    response = get("https://api.bscscan.com/api", params=params).json().get("result")
    if isinstance(response, str):
        ppaint(f"[#white]Ops, something went wrong!\n[#red]{response}\n")
        exit()
    timestamp = lambda x: datetime.timestamp(x)
    lottery = [
        (
            hex(int(data.get("data")[2:66], 16)),
            int(data.get("data")[66:130], 16),
        )
        for data in response
        if timestamp(from_date) <= int(data.get("timeStamp"), 0) <= timestamp(to_date)
    ]
    return lottery, lottery_number(from_date), from_date, to_date


def get_winners(date, lottery):
    """Get winner from transactions"""
    params = {
        "module": "logs",
        "action": "getLogs",
        "topic0": "0xb94bf7f9302edf52a596286915a69b4b0685574cffdedd0712e3c62f2550f0ba",
        "address": TICKET_ADDRESS,
        "fromBlock": date_to_block(date),
        "apikey": API_KEY,
    }
    response = get("https://api.bscscan.com/api", params=params).json().get("result")
    return {
        hex(int(data.get("data")[-104:-64], 16)): int(data.get("data")[-64:], 16)
        for data in response
        if int(data.get("data")[2:66], 16) == lottery - 5
    }


# ---- Overview


def lottery_overview(lottery):
    """Get unique wallets"""
    overview = dict()
    for who, amount in lottery:
        overview[who] = overview.get(who, 0) + amount
    return overview


def lottery_summary(overview, my_wallet):
    """Show current summary"""
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
        f"> [#cyan]{players:>3}[/] wallet(s) bet [#green]{ticket:>3}[/] ticket(s) "
        f"with [#blue]{win_probability(ticket, total_ticket, len(overview)):>6.2%}[/] "
        "winning probability"
        + (" [!cyan #white] YOU [/]" if ticket == ticket_own else "")
        for ticket, players in summary.items()
    )
    ppaint(string)


def print_winners(summary, winners):
    string = "\n".join(
        f"> [#cyan]{len(generations):>3}[/] wallet(s) of [#cyan]"
        f"{summary.get(tickets):>3}[/] with [#green]{tickets:>3}[/] "
        f"ticket(s) won an egg! [Gen {', '.join(map(str,generations))}]"
        for tickets, generations in winners.items()
    )
    ppaint(string)
