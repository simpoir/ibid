# Copyright (c) 2010, Max Rabkin
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from random import choice
from traceback import format_exception, format_exception_only

from ibid.plugins import Processor, match, authorise

features = {'debug': {
    'description': u'Help track bugs in the bot',
    'categories': ('debug',),
}}

last_exc_event = None

class SetLastException(Processor):
    # Come after everything. We don't modify events, and we want to catch
    # exceptions even in post-processors.
    priority = 10000

    def process(self, event):
        global last_exc_event

        if 'exc_info' in event:
            last_exc_event = event

class LastException(Processor):
    features = (u'debug',)
    usage = u"""last exception
    last traceback
    last bad event"""

    permission = u'debug'

    @match(r'^last (exception|trac[ek]back|bad event)$')
    @authorise()
    def exception(self, event, kind):
        exc_event = last_exc_event
        if exc_event is None:
            event.addresponse(choice((u'Are you *looking* for trouble?',
                                      u"I'll make an exception for you.")))
        else:
            if kind.lower() == 'exception':
                try:
                    lines = [u'%(type)s event "%(message)s" triggered ' %
                             {'type': exc_event.type,
                              'message': exc_event.message['raw']}]
                except KeyError:
                    lines = [u'%(type)s event triggered' % exc_event.type]

                lines += format_exception_only(*exc_event['exc_info'][:2])
            elif 'event' in kind.lower():
                lines = [u'%s: %r\n' % item for item in exc_event.iteritems()]
            else:
                lines = format_exception(*exc_event['exc_info'])
            event.addresponse(unicode(''.join(lines)[:-1]), conflate=False)
