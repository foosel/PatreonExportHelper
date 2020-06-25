Big thanks to

{% for patron in patrons | sort(attribute='display_name') %}
  * {% if patron.twitter %}[{{ patron.display_name | trim() }}](https://twitter/{{ patron.twitter | trim() }}){% else %}{{ patron.display_name | trim() }}{% endif %} (since {{ patron.start }})
{% endfor %}
