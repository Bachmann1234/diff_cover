# Diff Quality
## Quality Report: {{ report_name }}
## Diff: {{ diff_name }}

{% if src_stats %}
{% for src_path, stats in src_stats|dictsort %}
{% if stats.percent_covered < 100 %}
- {{ src_path }} ({{ stats.percent_covered|round(1) }}%):
{% for line, message in stats.violations %}
  - {{ src_path }}:{{ line }}: {{ message }}
{% endfor %}
{% else %}
- {{ src_path }} (100%)
{% endif %}
{% endfor %}

- **Total**:   {{ total_num_lines }} line{{ total_num_lines|pluralize }}
- **Violations**: {{ total_num_violations }} line{{ total_num_violations|pluralize }}
- **% Quality**: {{ total_percent_covered }}%

{% else %}
No lines with quality information in this diff.
{% endif %}
