from itertools import combinations
from re import match
from sys import argv

from colorifix.colorifix import paint
from requests import get

# 1st week starting block: 10854918

API_KEY = "W7T86S5W1EMKD4CGNPIU6QKSAUFQS5TADX"
ADDRESS = "0x50a1b4C905834291398a8dD140fa4A9AA9521f07"  # Kryptomon wallet


def get_transactions():
    """Get all last kryptomon transactions"""
    params = {
        "module": "account",
        "action": "txlist",
        "address": ADDRESS,
        "startblock": argv[1],
        "sort": "asc",
        "apikey": API_KEY,
    }
    response = get("https://api.bscscan.com/api", params=params).json().get("result")
    if isinstance(response, str):
        paint(f"[#white]Ops, somethig went wrong!\n[#red]{response}", True)
        exit(-1)
    lottery = [
        (int(data.get("blockNumber")), data.get("from"))
        for data in response
        if match("0x3fd43098", data.get("input"))
    ]
    return lottery


def get_tickets_blocks(blocks):
    """Get data from transactions block"""
    start, end = blocks[0], blocks[-1]
    params = {
        "module": "logs",
        "action": "getLogs",
        "fromBlock": start,
        "toBlock": end,
        "address": ADDRESS,
        "apikey": API_KEY,
    }
    response = get("https://api.bscscan.com/api", params=params).json().get("result")
    return {
        int(data.get("blockNumber"), 0): int(data.get("data"), 0)
        for data in response
        if int(data.get("blockNumber"), 0) in blocks
    }


def lottery_overview(lottery):
    """Get unique wallets"""
    overview = dict()
    transactions = get_tickets_blocks([block for block, _ in lottery])
    for block, who in lottery:
        bet_ticket = overview.get(who, 0)
        overview[who] = bet_ticket + transactions.get(block)
    return overview


def lottery_summary(overview, victory_probabilities):
    """Show current summary"""
    tickets = list(overview.values())
    summary = {tck: tickets.count(tck) for tck in set(tickets)}
    return "\n".join(
        f"> [#magenta]{players:>3}[/] player(s) bet [#green]{ticket:>3}[/] ticket(s)"
        f" with [#blue]{victory_probabilities.get(ticket):>5.1%}[/] "
        "victory probability"
        for ticket, players in summary.items()
    )


def victory_probability(summary, add=None):
    """Calculate vicorty probabilities: combinations filtered for single victory"""
    if add:
        summary["new"] = int(add)
    pool = sum([[who] * tickets for who, tickets in summary.items()], [])
    eggs_drop = round(len(summary) / 10)
    scenarios = [
        data for data in combinations(pool, eggs_drop) if len(data) == len(set(data))
    ]
    unique_better = {
        [who for who, t in summary.items() if t == ticket][0]: ticket
        for ticket in set(summary.values())
    }
    probs = {
        ticket: len([0 for scenario in scenarios if player in scenario])
        for player, ticket in unique_better.items()
    }
    total_scenarios = sum(probs.values())
    return {ticket: victory / total_scenarios for ticket, victory in probs.items()}


def main():
    if not (1 < len(argv) < 4):
        paint(
            "[#red @bold]USAGE[/@]: python kryptomon.py BLOCK_NUMBER (TICKET_TO_BET)\n"
            "Example: pyhthon kryptomon.py 10854918\n[#white]Check [@underline]https://"
            "bscscan.com/txs?a=0x50a1b4C905834291398a8dD140fa4A9AA9521f07[/@] for "
            "block number",
            True,
        )
        exit()
    lottery = get_transactions()
    message = (
        "\n[@underline @bold #blue]Kryptomon Lottery\n\n"
        f"[/ #white]Transactions found: [#red]{len(lottery)}"
    )
    paint(message, True)
    overview = lottery_overview(lottery)
    tickets, players = sum(overview.values()), len(overview)
    paint(
        f"Tickets bet [#red]{tickets}[/] by [#red]{players}[/] players for "
        f"[#red]{round(players / 10)}[/] eggs:",
        True,
    )
    paint(lottery_summary(overview, victory_probability(overview)), True)
    print()
    if len(argv) == 3 and argv[2].isdigit():
        tickets = int(argv[2])
        new_probabilities = victory_probability(overview, tickets)
        paint(
            f"If you bet [#magenta]{tickets}[/] ticket(s) right now, you'll have "
            f"[#blue]{new_probabilities.get(tickets):.1%}[/] victory probability",
            True,
        )
        print()


if __name__ == "__main__":
    main()
