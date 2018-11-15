# -*- coding: utf-8 -*-

"""
Jewish calendrical times for a given location.

HDate calculates and generates a represantation either in English or Hebrew
of the Jewish calendrical times for a given location
"""
from __future__ import division

import datetime as dt
import math
import sys

from dateutil import tz

from hdate import htables
from hdate.common import Location
from hdate.date import HDate


class Zmanim(object):  # pylint: disable=useless-object-inheritance
    """Return Jewish day times."""

    def __init__(self, date=dt.datetime.now(), location=Location(),
                 hebrew=True):
        """Initialize the Zmanim object."""
        self.location = location
        self.hebrew = hebrew
        self.shabbes_offset = 20

        if isinstance(date, dt.datetime):
            self.date = date.date()
            self.time = date.replace(tzinfo=location.timezone)
        elif isinstance(date, dt.date):
            self.date = date
            self.time = dt.datetime.now().replace(tzinfo=location.timezone)
        else:
            raise TypeError

    def __unicode__(self):
        """Return a Unicode representation of Zmanim."""
        return u"".join([
            u"{} - {}\n".format(
                zman.description[self.hebrew],
                self.zmanim[zman.zman].time()) for zman in htables.ZMANIM])

    def __str__(self):
        """Return a string representation of Zmanim."""
        if sys.version_info.major < 3:
            # pylint: disable=undefined-variable
            return unicode(self).encode('utf-8')  # noqa: F821

        return self.__unicode__()

    def __repr__(self):
        """Return a representation of Zmanim for programmatic use."""
        return ("Zmanim(date={}, location={}, hebrew={})".format(
            repr(self.time.replace(tzinfo=None)), repr(self.location),
            self.hebrew))

    def __eq__(self, other):
        """Override equality operator."""
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        """Override inequality operator."""
        return not self.__eq__(other)

    @property
    def zmanim(self):
        """Return a dictionary of the zmanim the object represents."""
        return {key: self.utc_minute_timezone(value) for
                key, value in self.get_utc_sun_time_full().items()}

    @property
    def issur_melacha_in_effect(self):
        """At the given time, return whether issur melacha is in effect."""
        weekday = self.date.weekday()
        tomorrow = self.date + dt.timedelta(days=1)
        tomorrow_holiday_type = HDate(
            gdate=tomorrow, diaspora=self.location.diaspora).holiday_type
        today_holiday_type = HDate(
            gdate=self.date, diaspora=self.location.diaspora).holiday_type

        if weekday == 4 or tomorrow_holiday_type == 1:
            if self.time > (self.zmanim["sunset"] -
                            dt.timedelta(minutes=self.shabbes_offset)):
                return True
        if weekday == 5 or today_holiday_type == 1:
            if self.time < self.zmanim["three_stars"]:
                return True
        return False

    def gday_of_year(self):
        """Return the number of days since January 1 of the given year."""
        return (self.date - dt.date(self.date.year, 1, 1)).days

    def utc_minute_timezone(self, minutes_from_utc):
        """Return the local time for a given time UTC."""
        from_zone = tz.gettz('UTC')
        to_zone = self.location.timezone
        utc = dt.datetime.combine(self.date, dt.time()) + \
            dt.timedelta(minutes=minutes_from_utc)
        utc = utc.replace(tzinfo=from_zone)
        local = utc.astimezone(to_zone)
        return local

    def _get_utc_sun_time_deg(self, deg):
        """
        Return the sunset and sunrise times in minutes from 00:00 (utc).

        This is done for a given sun altitude in sunrise `deg` degrees
        This function only works for altitudes sun really is.
        If the sun never gets to this altitude, the returned sunset and sunrise
        values will be negative. This can happen in low altitude when latitude
        is nearing the poles in winter times, the sun never goes very high in
        the sky there.
        """
        gama = 0        # location of sun in yearly cycle in radians
        eqtime = 0      # difference betwen sun noon and clock noon
        decl = 0        # sun declanation
        hour_angle = 0  # solar hour angle
        sunrise_angle = math.pi * deg / 180.0  # sun angle at sunrise/set

        # get the day of year
        day_of_year = self.gday_of_year()

        # get radians of sun orbit around earth =)
        gama = 2.0 * math.pi * ((day_of_year - 1) / 365.0)

        # get the diff betwen suns clock and wall clock in minutes
        eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gama) -
                           0.032077 * math.sin(gama) -
                           0.014615 * math.cos(2.0 * gama) -
                           0.040849 * math.sin(2.0 * gama))

        # calculate suns declanation at the equater in radians
        decl = (0.006918 - 0.399912 * math.cos(gama) +
                0.070257 * math.sin(gama) -
                0.006758 * math.cos(2.0 * gama) +
                0.000907 * math.sin(2.0 * gama) -
                0.002697 * math.cos(3.0 * gama) +
                0.00148 * math.sin(3.0 * gama))

        # we use radians, ratio is 2pi/360
        latitude = math.pi * self.location.latitude / 180.0

        # the sun real time diff from noon at sunset/rise in radians
        try:
            hour_angle = (math.acos(
                math.cos(sunrise_angle) /
                (math.cos(latitude) * math.cos(decl)) -
                math.tan(latitude) * math.tan(decl)))
        # check for too high altitudes and return negative values
        except ValueError:
            return -720, -720

        # we use minutes, ratio is 1440min/2pi
        hour_angle = 720.0 * hour_angle / math.pi

        # get sunset/rise times in utc wall clock in minutes from 00:00 time
        # sunrise / sunset
        longitude = self.location.longitude
        return int(720.0 - 4.0 * longitude - hour_angle - eqtime), \
            int(720.0 - 4.0 * longitude + hour_angle - eqtime)

    def get_utc_sun_time_full(self):
        """Return a list of Jewish times for the given location."""
        # sunset and rise time
        sunrise, sunset = self._get_utc_sun_time_deg(90.833)

        # shaa zmanit by gara, 1/12 of light time
        sun_hour = (sunset - sunrise) // 12
        midday = (sunset + sunrise) // 2

        # get times of the different sun angles
        first_light, _ = self._get_utc_sun_time_deg(106.1)
        talit, _ = self._get_utc_sun_time_deg(101.0)
        _, first_stars = self._get_utc_sun_time_deg(96.0)
        _, three_stars = self._get_utc_sun_time_deg(98.5)
        mga_sunhour = (midday - first_light) / 6

        res = dict(sunrise=sunrise, sunset=sunset, sun_hour=sun_hour,
                   midday=midday, first_light=first_light, talit=talit,
                   first_stars=first_stars, three_stars=three_stars,
                   plag_mincha=sunset - 1.25 * sun_hour,
                   stars_out=sunset + 18. * sun_hour / 60.,
                   small_mincha=sunrise + 9.5 * sun_hour,
                   big_mincha=sunrise + 6.5 * sun_hour,
                   mga_end_shma=first_light + mga_sunhour * 3.,
                   gra_end_shma=sunrise + sun_hour * 3.,
                   mga_end_tfila=first_light + mga_sunhour * 4.,
                   gra_end_tfila=sunrise + sun_hour * 4.,
                   midnight=midday + 12 * 60.)
        return res
