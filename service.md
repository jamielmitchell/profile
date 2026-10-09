---
title: Service
permalink: /service/
---

## Peer Review

<!--
  Combines reviews from ORCID (updated automatically) with the ones you list in
  _data/peer_reviews_manual.yml. To add a review, edit that file, not this one.
-->
{% assign reviews = site.data.peer_reviews | default: empty %}
{% if site.data.peer_reviews_manual %}{% assign reviews = reviews | concat: site.data.peer_reviews_manual %}{% endif %}
{% assign journals = reviews | group_by: "journal" | sort_natural: "name" %}
{% if journals.size > 0 %}
Ad hoc reviewer for:
{% for j in journals %}{% assign years = j.items | map: "year" | uniq | sort %}
- *{{ j.name }}* ({{ years | join: ", " }})
{% endfor %}
{% endif %}

## Leadership

**2026–Present · Communications Committee Member, [Flux Society](https://fluxsociety.org/)**<br>
Developmental Cognitive Neuroscience Society

**2022–2026 · GSE Mentorship Program Co-Chair, Stanford University**

- Coordinated mentorship pairings
- Planned regular events to facilitate mentorship opportunities for mentors and mentees

**2020 · Conference Facilitator, Stanford University**<br>
Conference: Build Together, Learn Better

- Facilitated a series of virtual convenings for San Jose students with learning differences and their families, Silicon Valley technology partners, and education leaders

## Mentorship

**2021–Present · Student Mentor, Stanford University**

- Various 1st year Ph.D. students and Master's students through the GSE Mentorship Program (2021–2026)
- Psychology Honors Program Thesis Advisor
- NeURO Fellowship Project Advisor
- Symbolic Systems Summer Internship Advisor
- Mentor for independent local high school research project
