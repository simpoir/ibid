# Copyright (c) 2009-2010, Michael Gorven, Stefano Rivera
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from subprocess import Popen, PIPE
from urllib import urlencode
import logging
import re

import ibid
from ibid.plugins import Processor, handler, match
from ibid.config import Option
from ibid.utils import file_in_path, unicode_output, human_join
from ibid.utils.html import get_country_codes, get_html_parse_tree

help = {}
log = logging.getLogger('plugins.conversions')

help['base'] = u'Convert numbers between bases (radixes)'
class BaseConvert(Processor):
    u"""[convert] <number> [from base <number>] to base <number>
    [convert] ascii <text> to base <number>
    [convert] <sequence> from base <number> to ascii"""

    feature = "base"

    abbr_named_bases = {
            "hex": 16,
            "dec": 10,
            "oct": 8,
            "bin": 2,
    }

    base_names = {
            2: "binary",
            3: "ternary",
            4: "quaternary",
            6: "senary",
            8: "octal",
            9: "nonary",
            10: "decimal",
            12: "duodecimal",
            16: "hexadecimal",
            20: "vigesimal",
            30: "trigesimal",
            32: "duotrigesimal",
            36: "hexatridecimal",
    }
    base_values = {}
    for value, name in base_names.iteritems():
        base_values[name] = value

    numerals = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+/"
    values = {}
    for value, numeral in enumerate(numerals):
        values[numeral] = value

    def _in_base(self, num, base):
        "Recursive base-display formatter"
        if num == 0:
            return "0"
        return self._in_base(num // base, base).lstrip("0") + self.numerals[num % base]

    def _from_base(self, num, base):
        "Return a base-n number in decimal. Needed as int(x, n) only works for n<=36"

        if base <= 36:
            num = num.upper()

        decimal = 0
        for digit in num:
            decimal *= base
            if self.values[digit] >= base:
                raise ValueError("'%s' is not a valid digit in %s" % (digit, self._base_name(base)))
            decimal += self.values[digit]

        return decimal

    def _parse_base(self, base):
        "Parse a base in the form of 'hex' or 'base 13' or None"

        if base is None:
            base = 10
        elif len(base) == 3 and base in self.abbr_named_bases:
            base = self.abbr_named_bases[base]
        elif base in self.base_values:
            base = self.base_values[base]
        elif base.startswith(u"base"):
            base = int(base.split()[-1])
        else:
            # The above should be the only cases allowed by the regex
            # This exception indicates programmer error:
            raise ValueError("Unparsable base: " + base)

        return base

    def _base_name(self, base):
        "Shows off the bot's smartypants heritage by naming bases"

        base_name = u"base %i" % base

        if base in self.base_names:
            base_name = self.base_names[base]

        return base_name

    def setup(self):
        bases = []
        for number, name in self.base_names.iteritems():
            if name[:3] in self.abbr_named_bases and self.abbr_named_bases[name[:3]] == number:
                bases.append(r"%s(?:%s)?" % (name[:3], name[3:]))
            else:
                bases.append(name)
        bases = "|".join(bases)

        self.base_conversion.im_func.pattern = re.compile(
            r"^(?:convert\s+)?([0-9a-zA-Z+/]+)\s+(?:(?:(?:from|in)\s+)?(base\s+\d+|%s)\s+)?(?:in|to|into)\s+(base\s+\d+|%s)\s*$"
            % (bases, bases), re.I)

        self.ascii_decode.im_func.pattern = re.compile(
            r"^(?:convert\s+)?ascii\s+(.+?)(?:(?:\s+(?:in|to|into))?\s+(base\s+\d+|%s))?$" % bases, re.I)

        self.ascii_encode.im_func.pattern = re.compile(
            r"^(?:convert\s+)?([0-9a-zA-Z+/\s]+?)(?:\s+(?:(?:from|in)\s+)?(base\s+\d+|%s))?\s+(?:in|to|into)\s+ascii$" % bases, re.I)

    @handler
    def base_conversion(self, event, number, base_from, base_to):
        "Arbitrary (2 <= base <= 64) numeric base conversions."

        base_from = self._parse_base(base_from)
        base_to = self._parse_base(base_to)

        if min(base_from, base_to) < 2 or max(base_from, base_to) > 64:
            event.addresponse(u'Sorry, valid bases are between 2 and 64, inclusive')
            return

        try:
            number = self._from_base(number, base_from)
        except ValueError, e:
            event.addresponse(unicode(e))
            return

        event.addresponse(u'That is %(result)s in %(base)s', {
            'result': self._in_base(number, base_to),
            'base': self._base_name(base_to),
        })

    @handler
    def ascii_decode(self, event, text, base_to):
        "Display the values of each character in an ASCII string"

        base_to = self._parse_base(base_to)

        if len(text) > 2 and text[0] == text[-1] and text[0] in ("'", '"'):
            text = text[1:-1]

        output = u""
        for char in text:
            code_point = ord(char)
            if code_point > 255:
                output += u'U%s ' % self._in_base(code_point, base_to)
            else:
                output += self._in_base(code_point, base_to) + u" "

        output = output.strip()

        event.addresponse(u'That is %(result)s in %(base)s', {
            'result': output,
            'base': self._base_name(base_to),
        })

        if base_to == 64 and [True for plugin in ibid.processors if getattr(plugin, 'feature', None) == 'base64']:
            event.addresponse(u'If you want a base64 encoding, use the "base64" feature')

    @handler
    def ascii_encode(self, event, source, base_from):

        base_from = self._parse_base(base_from)

        output = u""
        buf = u""

        def process_buf(buf):
            char = self._from_base(buf, base_from)
            if char > 127:
                raise ValueError(u"I only deal with the first page of ASCII (i.e. under 127). %i is invalid." % char)
            elif char < 32:
                return u" %s " % "NUL SOH STX EOT ENQ ACK BEL BS HT LF VT FF SO SI DLE DC1 DC2 DC2 DC4 NAK SYN ETB CAN EM SUB ESC FS GS RS US".split()[char]
            elif char == 127:
                return u" DEL "
            return unichr(char)

        try:
            for char in source:
                if char == u" ":
                    if len(buf) > 0:
                        output += process_buf(buf)
                        buf = u""
                else:
                    buf += char
                    if (len(buf) == 2 and base_from == 16) or (len(buf) == 3 and base_from == 8) or (len(buf) == 8 and base_from == 2):
                        output += process_buf(buf)
                        buf = u""

            if len(buf) > 0:
                output += process_buf(buf)
        except ValueError, e:
            event.addresponse(unicode(e))
            return

        event.addresponse(u'That is "%s"', output)
        if base_from == 64 and [True for plugin in ibid.processors if getattr(plugin, 'feature', None) == 'base64']:
            event.addresponse(u'If you want a base64 encoding, use the "base64" feature')

help['units'] = 'Converts values between various units.'
class Units(Processor):
    u"""convert [<value>] <unit> to <unit>"""
    feature = 'units'
    priority = 10

    units = Option('units', 'Path to units executable', 'units')

    temp_scale_names = {
        'fahrenheit': 'tempF',
        'f': 'tempF',
        'celsius': 'tempC',
        'celcius': 'tempC',
        'c': 'tempC',
        'kelvin': 'tempK',
        'k': 'tempK',
        'rankine': 'tempR',
        'r': 'tempR',
    }

    temp_function_names = set(temp_scale_names.values())

    def setup(self):
        if not file_in_path(self.units):
            raise Exception("Cannot locate units executable")

    def format_temperature(self, unit):
        "Return the unit, and convert to 'tempX' format if a known temperature scale"

        lunit = unit.lower()
        if lunit in self.temp_scale_names:
            unit = self.temp_scale_names[lunit]
        elif lunit.startswith("deg") and " " in lunit and lunit.split(None, 1)[1] in self.temp_scale_names:
            unit = self.temp_scale_names[lunit.split(None, 1)[1]]
        return unit

    @match(r'^convert\s+(-?[0-9.]+)?\s*(.+)\s+(?:in)?to\s+(.+)$')
    def convert(self, event, value, frm, to):

        # We have to special-case temperatures because GNU units uses function notation
        # for direct temperature conversions
        if self.format_temperature(frm) in self.temp_function_names \
                and self.format_temperature(to) in self.temp_function_names:
            frm = self.format_temperature(frm)
            to = self.format_temperature(to)

        if value is not None:
            if frm in self.temp_function_names:
                frm = "%s(%s)" % (frm, value)
            else:
                frm = '%s %s' % (value, frm)

        units = Popen([self.units, '--verbose', '--', frm, to], stdout=PIPE, stderr=PIPE)
        output, error = units.communicate()
        code = units.wait()

        output = unicode_output(output)
        result = output.splitlines()[0].strip()

        if code == 0:
            event.addresponse(result)
        elif code == 1:
            if result == "conformability error":
                event.addresponse(u"I don't think %(from)s can be converted to %(to)s", {
                    'from': frm,
                    'to': to,
                })
            elif result.startswith("conformability error"):
                event.addresponse(u"I don't think %(from)s can be converted to %(to)s: %(error)s", {
                    'from': frm,
                    'to': to,
                    'error': result.split(":", 1)[1],
                })
            else:
                event.addresponse(u"I can't do that: %s", result)

help['currency'] = u'Converts amounts between currencies.'
class Currency(Processor):
    u"""exchange <amount> <currency> for <currency>
    currencies for <country>"""

    feature = "currency"

    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'http://www.xe.com/'}
    currencies = {}
    country_codes = {}

    def _load_currencies(self):
        etree = get_html_parse_tree('http://www.xe.com/iso4217.php', headers=self.headers, treetype='etree')

        tbl_main = [x for x in etree.getiterator('table') if x.get('class') == 'tbl_main'][0]

        self.currencies = {}
        for tbl_sub in tbl_main.getiterator('table'):
            if tbl_sub.get('class') == 'tbl_sub':
                for tr in tbl_sub.getiterator('tr'):
                    code, place = [x.text for x in tr.getchildren()]
                    name = u''
                    if not place:
                        place = u''
                    if u',' in place[1:-1]:
                        place, name = place.split(u',', 1)
                    place = place.strip()
                    if code in self.currencies:
                        currency = self.currencies[code]
                        # Are we using another country's currency?
                        if place != u'' and name != u'' and (currency[1] == u'' or currency[1].rsplit(None, 1)[0] in place
                                or (u'(also called' in currency[1] and currency[1].split(u'(', 1)[0].rsplit(None, 1)[0] in place)):
                            currency[0].insert(0, place)
                            currency[1] = name.strip()
                        else:
                            currency[0].append(place)
                    else:
                        self.currencies[code] = [[place], name.strip()]

        # Special cases for shared currencies:
        self.currencies['EUR'][0].insert(0, u'Euro Member Countries')
        self.currencies['XOF'][0].insert(0, u'Communaut\xe9 Financi\xe8re Africaine')
        self.currencies['XOF'][1] = u'Francs'

    strip_currency_re = re.compile(r'^[\.\s]*([\w\s]+?)s?$', re.UNICODE)

    def _resolve_currency(self, name, rough=True):
        "Return the canonical name for a currency"

        if name.upper() in self.currencies:
            return name.upper()

        m = self.strip_currency_re.match(name)

        if m is None:
            return False

        name = m.group(1).lower()

        # TLD -> country name
        if rough and len(name) == 2 and name.upper() in self.country_codes:
           name = self.country_codes[name.upper()].lower()

        # Currency Name
        if name == u'dollar':
            return "USD"

        name_re = re.compile(r'^(.+\s+)?\(?%ss?\)?(\s+.+)?$' % name, re.I | re.UNICODE)
        for code, (places, currency) in self.currencies.iteritems():
            if name_re.match(currency) or [True for place in places if name_re.match(place)]:
                return code

        return False

    @match(r'^(exchange|convert)\s+([0-9.]+)\s+(.+)\s+(?:for|to|into)\s+(.+)$')
    def exchange(self, event, command, amount, frm, to):
        if not self.currencies:
            self._load_currencies()

        if not self.country_codes:
            self.country_codes = get_country_codes()

        rough = command.lower() == 'exchange'

        canonical_frm = self._resolve_currency(frm, rough)
        canonical_to = self._resolve_currency(to, rough)
        if not canonical_frm or not canonical_to:
            if rough:
                event.addresponse(u"Sorry, I don't know about a currency for %s", (not canonical_frm and frm or to))
            return

        data = {'Amount': amount, 'From': canonical_frm, 'To': canonical_to}
        etree = get_html_parse_tree('http://www.xe.com/ucc/convert.cgi', urlencode(data), self.headers, 'etree')

        result = [tag.text for tag in etree.getiterator('h2')]
        if result:
            event.addresponse(u'%(fresult)s (%(fcountry)s %(fcurrency)s) = %(tresult)s (%(tcountry)s %(tcurrency)s)', {
                'fresult': result[0],
                'tresult': result[2],
                'fcountry': self.currencies[canonical_frm][0][0],
                'fcurrency': self.currencies[canonical_frm][1],
                'tcountry': self.currencies[canonical_to][0][0],
                'tcurrency': self.currencies[canonical_to][1],
            })
        else:
            event.addresponse(u"The bureau de change appears to be closed for lunch")

    @match(r'^(?:currency|currencies)\s+for\s+(?:the\s+)?(.+)$')
    def currency(self, event, place):
        if not self.currencies:
            self._load_currencies()

        search = re.compile(place, re.I)
        results = []
        for code, (places, name) in self.currencies.iteritems():
            for place in places:
                if search.search(place):
                    results.append(u'%s uses %s (%s)' % (place, name, code))
                    break

        if results:
            event.addresponse(human_join(results))
        else:
            event.addresponse(u'No currencies found')

# vi: set et sta sw=4 ts=4: