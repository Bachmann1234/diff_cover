{% for src_path, stats in src_stats|dictsort %}
{% if stats.snippets_html %}

## {{ src_path }}
{% for snippet in stats.snippets_html %}

{{ snippet }}

---

{% endfor %}

{% endif %}
{% endfor %}
