import json
from decimal import ROUND_HALF_EVEN, Decimal


def set_v(data, key, default):
    data[key] = data.get(key, default)


def truncate(value, precision):
    if precision == 0:
        return value
    q = Decimal(10) ** -precision
    return value.quantize(q, rounding=ROUND_HALF_EVEN)


# Thanks to example from python docs
def moneyfmt(value, places=2, curr="", sep=",", dp="."):
    """Convert Decimal to a money formatted string.

    places:  required number of places after the decimal point
    curr:    optional currency symbol before the sign (may be blank)
    sep:     optional grouping separator (comma, period, space, or blank)
    dp:      decimal point indicator (comma or period)
             only specify as blank when places is zero
    """
    q = Decimal(10) ** -places  # 2 places --> '0.01'
    sign, digits, _ = value.quantize(q).as_tuple()
    result = []
    digits = list(map(str, digits))
    build, next_digit = result.append, digits.pop
    for _ in range(places):
        build(next_digit() if digits else "0")
    if places:
        build(dp)
    if not digits:
        build("0")
    i = 0
    while digits:
        build(next_digit())
        i += 1
        if i == 3 and digits:
            i = 0
            build(sep)
    if curr:
        build(curr)
    if sign:
        build("-")
    return "".join(reversed(result))


class CurrencyTable:
    def __init__(self):
        self.data = {}
        self.load_data()

    def load_data(self):
        with open("api/ext/moneyformat/currencies.json") as f:
            contents = f.read()
        self.data = self.add_defaults(json.loads(contents))

    def add_defaults(self, data):
        return {k: self.add_default(entry) for k, entry in data.items()}  # set common defaults to reduce size of a json file

    def add_default(self, entry):
        if isinstance(entry, str):
            entry = {"name": entry}
        set_v(entry, "divisibility", 2)
        set_v(entry, "symbol", None)
        set_v(entry, "crypto", False)
        return entry

    def get_currency_data(self, currency, fallback=True):
        result = self.data.get(currency.upper())
        if not result and fallback:
            usd = self.get_currency_data("USD", fallback=False)
            return {
                "name": currency,
                "divisibility": usd["divisibility"],
                "symbol": None,
                "crypto": True,
            }
        return result

    def normalize(self, currency, value, divisibility=None):
        return truncate(value, divisibility or self.get_currency_data(currency)["divisibility"])

    def format_currency(self, currency, value, fancy=True, divisibility=None):
        if value is None or currency is None:
            return value
        currency_info = self.get_currency_data(currency)
        symbol = currency_info["symbol"]
        kwargs = {"places": divisibility if divisibility else currency_info["divisibility"], "sep": ""}
        if fancy:
            kwargs.update({"curr": symbol, "sep": ","})
        value = moneyfmt(value, **kwargs)
        if not fancy:
            return value
        if not symbol:
            return f"{value} {currency}"
        return f"{value} ({currency})"

    def format_decimal(self, currency, value, divisibility=None):
        if isinstance(value, str):
            value = Decimal(value)
        return self.format_currency(currency, value, fancy=False, divisibility=divisibility)


currency_table = CurrencyTable()
