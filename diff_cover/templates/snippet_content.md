{% for src_path, stats in src_stats|dictsort %}
{% if stats.snippets_text %}

## {{ src_path }}
{% for snippet in stats.snippets_text %}

{{ snippet }}

---

{% endfor %}

{% endif %}
{% endfor %}
