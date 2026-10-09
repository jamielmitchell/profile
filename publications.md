---
title: Publications
permalink: /publications/
redirect_from:
  - /publication/2020-07-09-PrevailingTheories
  - /publication/2024-12-13-DevAndValSRF
  - /publication/2025-01-15-Mitchell_VWFA_PrePrint
  - /publication/2025-05-07-Stone
  - /publication/2025-07-27-Mitchell_VWFA-methods_PrePrint
---

<!--
  This list updates itself from ORCID every week. You don't edit it here.
  To hide, fix, or add a publication, edit _data/publication_settings.yml.
-->

You can also find my work on [Google Scholar](https://scholar.google.com/citations?user=W2usbdQAAAAJ&hl=en) and [ORCID](https://orcid.org/0009-0002-0854-1875). My first-author work is highlighted.

<div class="pub-filter" role="group" aria-label="Filter publications">
  <button type="button" aria-pressed="true" data-filter="all">All</button>
  <button type="button" aria-pressed="false" data-filter="first">First author</button>
</div>

<div id="pub-list">
{% assign years = site.data.publications | group_by: "year" %}
{% for year in years %}
  {% assign firsts = year.items | where: "first_author", true %}
  <section class="pub-year" data-has-first="{% if firsts.size > 0 %}true{% else %}false{% endif %}">
    <h2>{{ year.name }}</h2>
    {% for pub in year.items %}{% include publication.html pub=pub %}{% endfor %}
  </section>
{% endfor %}
</div>

<script>
  document.querySelectorAll(".pub-filter button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".pub-filter button").forEach(function (b) {
        b.setAttribute("aria-pressed", b === btn);
      });
      document.getElementById("pub-list").classList.toggle("first-only", btn.dataset.filter === "first");
    });
  });
</script>
