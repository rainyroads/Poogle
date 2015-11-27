import logging

import re

from poogle.errors import PoogleParserError, PoogleError


class PoogleResultsPage(object):

    def __init__(self, poogle, soup):
        """
        Args:
            poogle(poogle.Poogle):      The parent Poogle object
            soup(bs4.BeautifulSoup):    The search results page HTML soup.
        """
        self._poogle = poogle
        self._log = logging.getLogger('poogle.results_page')
        self._soup = soup
        self.results = []
        self.count = 0

        self.total_results = 0
        self.number = 0

        self._parse_results()

    def _parse_results(self):
        """
        Parse search results

        Raises:
            PoogleError:    Raised if the search results can not be parsed for any reason
        """
        # Result counts aren't critical, so unless we want strict parsing, we should swallow any errors parsing them
        try:
            self._parse_total_results_count()
        except PoogleError:
            if self._poogle.strict:
                raise

        results = self._soup.find(id='search').ol.find_all('li', {'class': 'g'})
        for result in results:
            try:
                self.results.append(PoogleResult(self, result))
            except PoogleParserError:
                self._log.info('Skipping unparsable result')
                continue

        self.count = len(self.results)

    def _parse_total_results_count(self):
        """
        Parse the (estimated) total number of search results found.

        Raises:
            PoogleParserError:  Raised if the search results count could not be parsed for any reason.
        """
        # Get the raw result count string
        self._log.debug('Parsing total results count from the search results page')
        try:
            stats = self._soup.find(id='resultStats').text
        except Exception as e:
            self._log.warn('An error occurred while parsing the total results count: %s', e.message)
            raise PoogleParserError(e.message)
        self._log.debug('Results text matched: %s', stats)

        # Parse the result count
        match = re.match(r'^[\w\s]+?(?P<count>\d+(,\d+)*)[\w\s]+$', stats)
        if not match or not match.group('count'):
            self._log.error('Unrecognized total results format: %s', stats)
            raise PoogleParserError('Unrecognized total results format: {f}'.format(f=stats))

        self.total_results = int(match.group('count').replace(',', ''))
        self._log.info('Total results count successfully parsed: %d', self.total_results)

    def _parse_page_number(self):
        """
        Parse the current page number.

        Raises:
            PoogleParserError:  Raised if strict parsing is enabled and the page number could not be parsed.
        """
        tds = self._soup.find(id='foot').find_all('td')
        for td in tds:
            if not td.a and td.text.isdigit():
                self.number = int(td.text)
                self._log.info('Page number parsed: %d', self.number)
                break
        else:
            self._log.warn('Unable to parse the current page number')
            if self._poogle.strict:
                raise PoogleParserError('Unable to parse the current page number')

    def __len__(self):
        return self.count

    def __repr__(self):
        return '<PoogleResultsPage Container: Page {num}>'.format(num=self.number)


class PoogleResult(object):

    def __init__(self, page, soup):
        """
        Args:
            page(PoogleResultsPage):    The page this search result was found on
            soup(bs4.element.Tag):      The search result HTML soup
        """
        self._log = logging.getLogger('poogle.result')
        self._soup = soup
        self.page = page

        self.title = None
        self.url = None

        self._parse_result()

    def _parse_result(self):
        """
        Parse search result data

        Raises:
            PoogleParserError:  Raised if the result can not be parsed for any reason
        """
        self.title = self._soup.a.text
        self._log.info('Result title parsed: %s', self.title)

        # Make sure this is a valid result URL (and not a link to image results, as an example)
        href = self._soup.a.get('href')
        if not href.startswith('/url?'):
            raise PoogleParserError('Unrecognized URL format: %s', href)

        # We pull the URL from the cite tag, since the actual href from Google contains arbitrary query parameters
        self.url = self._soup.cite.text
        self._log.info('Result URL parsed: %s', self.url)

    def __repr__(self):
        return '<PoogleResult Container: {title}>'.format(title=self.title)

    def __str__(self):
        return '{title} :: {url}'.format(title=self.title, url=self.url)
