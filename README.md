# Patron Export Helper

Parses CSV Export of patrons from patreon.com, allows extracting patrons pledging for reward levels provided
on command line and rendering them to stdout using a provided jinja2 template file.

## Setup

Requires Python 3 and a bunch of dependencies:

    pip3 install -r requirements.txt

Installation into virtualenv is recommended.

## Usage



All patrons to output file:

    patronexport.py -i Members_somenumber.csv -t mytemplate.md -o output.md

Only patrons at reward levels "One Tier" and "Another Tier" to stdout:

    patronexport.py -i Members_somenumber.csv -t mytemplate.txt -r "One Tier" -r "Another Tier"

Only patrons at reward level "Another Tier" with mapping file to output file:

    patronexport.py -i Members_somenumber.csv -t mytemplate.md -r "Another Tier" -m mappingfile.yaml -o output.md

## Templates

Templates are Jinja2 templates.

Available template variables are:

  * `patrons`: List of all included patrons as `Patron` objects
  * `included`: Count of all included patrons
  * `excluded`: Count of all excluded patrons
  * `total`: Total count of all patrons
  * `reward_levels`: List of included reward levels

A `Patron` object has the following attributes:

  * `name`: User name on Patreon
  * `display_name`: Name from mapping, or addressee, or name
  * `email`: Mail address
  * `pledge`: Amount of pledge
  * `lifetime`: Amount of pledges already processed
  * `status`: `ok`, `declined` or `former`
  * `twitter`: Twitter handle without @
  * `street`: Street part of shipping address
  * `city`: City part of shipping address
  * `state`: State part of shipping address
  * `zip`: Zip part of shipping address
  * `country_code`: Country code part of shipping address (ISO3166)
  * `country`: Human readable version of country of shipping address
  * `phone`: Phone number
  * `start`: Start of patronage
  * `start_date`: Start of patronage as datetime object (parsed by dateutil)
  * `max`: Maximum monthly amount
  * `tier`: Name of pledge tier (as set up on Patreon)
  * `following`: Whether the patron is following you
  * `charge_frequency`: How often the user gets charged
  * `last_charge`: Date of last charge
  * `last_charge_date`: Date of last charge as datetime object (parsed by dateutil)
  * `details`: Additional details (from Relationship Manager?)
  * `id`: User id
  * `last_update`: Date of last update of user data
  * `last_update_date`: Date of last update of user data as datetime object (parsed by dateutil)

### Template example

```
Big thanks to

{% for patron in patrons | sort(attribute='display_name') %}
  * {% if patron.twitter %}[{{ patron.display_name | trim() }}](https://twitter/{{ patron.twitter | trim() }}){% else %}{{ patron.display_name | trim() }}{% endif %} (since {{ patron.start }})
{% endfor %}

```

## Mapping file

Sometimes it's necessary to adjust some of the metadata provided in the Patreon export, e.g. to list the user
under another name on some "Thank yo" list than the one associated with the Patreon account. This can be done
via a mapping file.

A mapping file is a YAML file that maps the email addresses of the affected Patrons to the overwritten metadata.
All of the `Patron` object properties besides `start_date` can be replaced this way. Only the fields present
in the mapping entry will be overwritten, all other fields will be left at the values taken from the
Patreon CSV export.

### Mapping example

```
someone@example.com:
  display_name: Some Company Name
someoneelse@example.com:
  addressee: J. Random Patron
```

## Changelog

### 2020-06-25

  * Adapted to new format from the Relationship Manager, as the old Patron Manager is being retired by Patreon and with
    it the old CSV export.

### 2019-10-21

  * Level filtering for additionals

### 2017-12-11

  * Support for non integer pledge levels thanks to Patreon's STUPID new fee model.

### 2017-01-20

  * Now supports an additional mapping file to overwrite Patron metadata based on
    email address.

### 2016-08-22

  * Adapted to new CSV export format provided by Patreon
    * Reward levels are now defined differently ("20.00+ Reward" => "20 + Reward")
    * Street names might contain a "None" suffix if no additional address information (e.g. apt number) was supplied, stripping that, probably a Patreon export bug
  * Detect changes in available columns & warn about it
  * More resilience for change in available columns

### 2016-07-20

  * Adapted to new CSV export format provided by Patreon
  * Added --until parameter

### 2016-06-14

  * Added address parsing
  * Added --start parameter
  * New dependencies: iso3166, python-dateutil

### 2016-04-21

  * Initial version

## License

BSD

## Source

https://github.com/foosel/PatreonExportHelper
