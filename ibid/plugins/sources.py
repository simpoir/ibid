import ibid
from ibid.plugins import Processor, match, authorise
from ibid.utils import human_join

help = {'sources': u'Controls and lists the configured sources.'}

class Admin(Processor):
    u"""(connect|disconnect) (to|from) <source>
    load <source> source"""
    feature = 'sources'

    permission = u'sources'

    @match(r'^connect\s+(?:to\s+)?(\S+)$')
    @authorise(fail_silently=True)
    def connect(self, event, source):
        if source not in ibid.sources:
            event.addresponse(u"I don't have a source called %s", source)
        elif ibid.sources[source].connect():
            event.addresponse(u'Connecting to %s', source)
        else:
            event.addresponse(u"I couldn't connect to %s", source)

    @match(r'^disconnect\s+(?:from\s+)?(\S+)$')
    @authorise(fail_silently=True)
    def disconnect(self, event, source):
        if source not in ibid.sources:
            event.addresponse(u"I am not connected to %s", source)
        elif ibid.sources[source].disconnect():
            event.addresponse(u'Disconnecting from %s', source)
        else:
            event.addresponse(u"I couldn't disconnect from %s", source)

    @match(r'^(?:re)?load\s+(\S+)\s+source$')
    @authorise(fail_silently=True)
    def load(self, event, source):
        if ibid.reloader.load_source(source, ibid.service):
            event.addresponse(u"%s source loaded", source)
        else:
            event.addresponse(u"Couldn't load %s source", source)

class Info(Processor):
    u"""(sources|list configured sources)"""
    feature = 'sources'

    @match(r'^sources$')
    def list(self, event):
        sources = []
        for name, source in ibid.sources.items():
            url = source.url()
            sources.append(url and u'%s (%s)' % (name, url) or name)
        event.addresponse(u'Sources: %s', human_join(sorted(sources)) or u'none')

    @match(r'^list\s+configured\s+sources$')
    def listall(self, event):
        event.addresponse(u'Configured sources: %s', human_join(sorted(ibid.config.sources.keys())) or u'none')

# vi: set et sta sw=4 ts=4:
