#!/usr/bin/env python
# coding=utf-8

from __future__ import print_function, absolute_import, unicode_literals


__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = """
Copyright (c) 2016, Gina Häußge
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."""


import click
import codecs
import jinja2
import unicodecsv
import dateutil.parser
import iso3166
import sys
import yaml
import os
import io


class Patron(object):

	_fields = ["name",
	           "email",
	           "twitter",
	           "status",
	           "lifetime",
	           "pledge",
	           "addressee",
	           "street",
	           "city",
	           "state",
	           "zip",
	           "country_code",
	           "phone",
	           "start",
	           "max",
	           "tier",
	           "following",
	           "charge_frequency",
	           "last_charge",
	           "last_charge_status",
	           "details",
	           "id",
	           "last_update"]

	def __init__(self, mapping=None, *args, **kwargs):
		if mapping is not None and "email" in kwargs and kwargs["email"] in mapping:
			mapped = mapping[kwargs["email"]]
		else:
			mapped = dict()

		data = dict((key, mapped[key] if key in mapped else value) for key, value in kwargs.items())

		for key in self.__class__._fields:
			setattr(self, key, None)

		#street = data.get("street", None)
		#if street and street.strip().endswith(" None"):
		#	street = street.strip()[:-len(" None")]
		#	data["street"] = street

		for key, value in data.items():
			if key not in self.__class__._fields:
				raise KeyError("Invalid field: {}".format(key))
			setattr(self, key, value)

		try:
			self.start_date = dateutil.parser.parse(self.start)
		except:
			print("Something went wrong while parsing start date for {}: {!r}".format(self.name, self.start), err=True)

		if self.last_charge:
			try:
				self.last_charge_date = dateutil.parser.parse(self.last_charge)
			except:
				click.echo("Something went wrong while parsing last charge date for {}: {!r}".format(self.name, self.start), err=True)

		if self.last_update:
			try:
				self.last_update_date = dateutil.parser.parse(self.last_update)
			except:
				click.echo("Something went wrong while parsing last update date for {}: {!r}".format(self.name, self.start), err=True)

		if "country" in mapped:
			self.country = mapped["country"]
		else:
			if self.country_code:
				if self.country_code == "GB":
					self.country = "United Kingdom"
				elif self.country_code == "TW":
					self.country = "Taiwan"
				else:
					try:
						self.country = iso3166.countries.get(self.country_code).name
					except:
						self.country = self.country_code
			else:
				self.country = "N/A"

		if "display_name" in mapped:
			self.display_name = mapped["display_name"]
		elif self.addressee:
			self.display_name = self.addressee
		else:
			self.display_name = self.name

	@classmethod
	def from_row(cls, row_dict, mapping=None):
		return cls(mapping=mapping, **row_dict)


class MissingColumns(Exception):
	pass


def map_column_names(names):
	MAP = {
		"patron status": "status",
		"lifetime $": "lifetime",
		"pledge $": "pledge",
		"country": "country_code",
		"patronage since date": "start",
		"max amount": "max",
		"follows you": "following",
		"charge frequency": "charge_frequency",
		"last charge date": "last_charge",
		"last charge status": "last_charge_status",
		"additional details": "details",
		"user id": "id",
		"last updated": "last_update"
	}
	return [MAP.get(x.lower(), x.lower()) for x in names]


def map_column_value(column, value):
	if column == "status":
		MAP = {
			"active patron": "ok",
			"declined patron": "declined",
			"former patron": "former"
		}
		return MAP.get(value.lower(), value.lower())
	elif column in ("lifetime", "pledge") and isinstance(value, str):
		if value.startswith("$"):
			value = value[1:]
		value = value.replace(",", "")
		return float(value)
	return value


def extract_patrons(filename, levels=None, also_declined=False, from_date=None, until_date=None, mapping=None):
	if levels is None:
		levels = []
	levels = list(map(lambda x: x.lower(), levels))

	click.echo("Filtering for levels {!r}".format(levels))

	if mapping is None:
		mapping = dict()

	from_date_object = dateutil.parser.parse(from_date + " 00:00:00") if from_date is not None else None
	until_date_object = dateutil.parser.parse(until_date + " 23:59:59") if until_date is not None else None

	count = 0
	patrons = list()
	with io.open(filename, "rb") as f:
		reader = unicodecsv.reader(f, encoding="utf-8", delimiter=',', quotechar='"')

		column_names = next(reader)
		mapped_column_names = map_column_names(column_names)
		valid_column_names = [name for name in mapped_column_names if name in Patron._fields]
		mapped_column_names_set = set(mapped_column_names)

		if mapped_column_names_set & set(Patron._fields) != mapped_column_names_set:
			added = [name for name in mapped_column_names if name not in valid_column_names]
			removed = [name for name in Patron._fields if name not in valid_column_names]

			click.echo("Changed columns detected in {}".format(filename))
			click.echo("\tadded: {}".format(", ".join(added)))
			click.echo("\tremoved: {}".format(", ".join(removed)))

			if removed:
				raise MissingColumns("Some columns got removed from the export, script needs to be adjusted")

		for row in reader:
			row_dict = dict(zip(mapped_column_names, row))

			try:
				row_dict = dict((k, map_column_value(k, v)) for k, v in row_dict.items())
				patron = Patron.from_row(dict((name, row_dict[name]) for name in valid_column_names), mapping=mapping)
			except Exception as exc:
				click.echo("Something went wrong while parsing and mapping {}: {}".format(row_dict.get("name"), exc), err=True)
				continue

			valid_status = patron.status == "ok" or (also_declined and patron.status == "declined")
			if not valid_status:
				continue

			if from_date is not None and patron.start_date < from_date_object:
				continue

			if until_date is not None and patron.start_date > until_date_object:
				continue

			count += 1
			if patron.tier.lower() not in levels:
				continue

			patrons.append(patron)

	return count, patrons


def extract_additionals(additionalfile, levels=None, mapping=None):
	if not additionalfile:
		return []

	if levels is None:
		levels = []
	levels = list(map(lambda x: x.lower(), levels))

	click.echo("Filtering additionals for levels {!r}".format(levels))

	if mapping is None:
		mapping = dict()

	if not os.path.exists(additionalfile):
		click.echo("Additional file {} does not exist!", err=True)
		sys.exit(-1)

	with codecs.open(additionalfile, errors="replace") as f:
		additionals = yaml.safe_load(f)

	patrons = []
	count = 0

	for additional in additionals.get("patrons", []):
		patron = Patron.from_row(dict((key, value) for key, value in additional.items() if key in Patron._fields),
		                         mapping=mapping)
		count += 1
		if patron.tier.lower() in levels:
			patrons.append(patron)
			click.echo("Added patron {} from additionals".format(patron.name))

	for name, count in additionals.get("counts", dict()).items():
		try:
			additional_count = int(count)
		except:
			print("Could not convert {} to an integer, skipping".format(count))
		else:
			print("Adding {} to number of supporters".format(additional_count))
			count += additional_count

	return count, patrons


def extract_mapping(mappingfile):
	if not mappingfile:
		return dict()

	if not os.path.exists(mappingfile):
		click.echo("Mapping file {} does not exist!", err=True)
		sys.exit(-1)

	with codecs.open(mappingfile, errors="replace") as f:
		mapping = yaml.safe_load(f)
	return mapping


def export(inputfile, templatefile, outputfile, rewards, also_declined, from_date, until_date, mappingfile=None, additionalfile=None):
	mapping = None
	if mappingfile is not None:
		mapping = extract_mapping(mappingfile)

	try:
		count, patrons = extract_patrons(inputfile,
		                                 levels=rewards,
		                                 also_declined=also_declined,
		                                 from_date=from_date,
		                                 until_date=until_date,
		                                 mapping=mapping)
	except MissingColumns:
		click.echo("Detected missing columns, aborting...", err=True)
		sys.exit(-1)

	if additionalfile is not None:
		addcount, additionals = extract_additionals(additionalfile, levels=rewards, mapping=mapping)
		count += addcount
		patrons += additionals

	click.echo("Found {} patrons, {} of which are included".format(count, len(patrons)))

	import os
	env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(os.path.abspath(__file__))),
	                         trim_blocks=True)
	templatefile = env.get_template(templatefile)
	rendered = templatefile.render(total=count,
	                               included=len(patrons),
	                               excluded=count - len(patrons),
	                               patrons=patrons,
	                               reward_levels=rewards)

	if outputfile is not None:
		with codecs.open(outputfile, "w", encoding="utf-8") as f:
			f.write(rendered)
	else:
		click.echo(rendered)

@click.command(context_settings=dict(ignore_unknown_options=True))
@click.option("--input", "-i", "inputfile", type=click.Path(), required=True, help="The patron export from Patreon as .csv file")
@click.option("--output", "-o", "outputfile", type=click.Path(), default=None, help="The output path")
@click.option("--template", "-t", "templatefile", type=click.Path(), required=True, help="The template path of the Jinja2 template to use")
@click.option("--reward", "-r", "rewards", multiple=True, type=str, default=None, help="The reward levels to include - textual name, case insensitive")
@click.option("--also-declined", "-d", "also_declined", is_flag=True, type=bool, default=False, help="Also include declined patrons in output")
@click.option("--from", "-f", "from_date", default=None, help="year-month-day of start date from which to output patrons")
@click.option("--until", "-", "until_date", default=None, help="year-month-day of start date until which to output patrons")
@click.option("--mapping", "-m", "mappingfile", default=None, type=click.Path(), help="Mapping file from mail to replacement patron metadata")
@click.option("--additional", "-a", "additionalfile", default=None, type=click.Path(), help="Additional manually managed patrons, as yaml file of CSV entries")
def export_command(inputfile, templatefile, outputfile, rewards, also_declined, from_date, until_date, mappingfile, additionalfile):
	export(inputfile, templatefile, outputfile, rewards, also_declined, from_date, until_date, mappingfile=mappingfile, additionalfile=additionalfile)

if __name__ == "__main__":
	export_command()
