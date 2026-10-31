---
name: cafe-growth-research
description: Research cafes from public map data, verify business details from official sources, and prepare factual Cafe Crypto Beans pitches with demo links.
---

# Cafe growth research

Use this skill to build a small, evidence-backed list of cafes and restaurants that may be a fit for Cafe Crypto Beans.

## Workflow

1. Ask for a specific city, district, or neighborhood and the desired category. Do not start a worldwide crawl or enumerate whole countries.
2. Use `beans-cafe-research.search_cafes_on_map` for a bounded OpenStreetMap lookup. The geocoded area and map records are discovery leads, not verified current business details.
3. Verify details that matter using the business's own website or an official business-controlled page. Do not infer missing values. Keep the official page URL beside every verified menu, logo, phone, and website field. Store logo URLs only; do not download or reuse logo artwork without permission.
4. Summarize menus rather than copying a full copyrighted menu. Do not bypass logins, paywalls, access controls, or robots/site terms. Use public business contact details only for relevant, individualized outreach; do not send messages or make contact without an explicit request.
5. Before writing lead records, show the candidate and source links and ask for confirmation unless the user has already explicitly asked to save those specific results. Then use `beans-cafe-research.save_cafe_lead`. Record uncertainty in notes and source only fields that the source actually supports.
6. Use `beans-cafe-research.get_beans_product_context` for product claims and the cafe demo URL. Draft a concise, tailored pitch based on that evidence; label it as a draft and never claim a cafe-specific demo is provisioned unless verified.
7. Use `beans-cafe-research.find_saved_cafes` to recall saved research. Update stale records only after checking their sources and keep source links and notes with the lead.

## Data and source rules

- The MCP search uses a user-requested, bounded area and caches responses. If the location resolves to a broad region, narrow it before searching.
- Attribute map-derived facts to OpenStreetMap and preserve the `© OpenStreetMap contributors` attribution. Follow the public Nominatim usage policy linked in the product documentation; its geocoder is not a bulk or systematic POI-export service.
- Map results may not contain logos, current menus, or current phone numbers. A blank field means unknown, not absent.
- Prefer first-party business sources for menu and contact verification. Record when information was checked, and distinguish map-reported data from official-source verification.
- Persist business research in the BEANS ads project's local SQLite memory. Do not save personal customer information or secrets.
- Product claims must come from the saved product profile and its cited source. The current site describes crypto payments, QR digital menus, sales/inventory/customer-trend analytics, and custom domains/branding/themes. Do not invent prices, integrations, compliance, guarantees, or settlement details.
- Demo links use `https://beanscoin.cafe/cafe/<slug>`. The route pattern is visible on the website, but a cafe-specific populated demo is not guaranteed by link generation alone.
