{#
    dbt prefixes a custom schema with the target one by default, which turns
    `marts` into `public_marts`. Another project reads these tables by name, so
    the custom schema is used as written.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
