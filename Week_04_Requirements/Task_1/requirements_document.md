# Software Requirements Specification

## Priority scale

- **Must**: essential for an acceptable release.
- **Should**: important, but a temporary workaround exists.
- **Could**: valuable enhancement if time and resources allow.
- **Won't**: explicitly deferred from this release.

## Requirements

### REQ-001: Material volume reporting (current) by category and location

**Priority:** Must

Provide a material-volume reporting capability for a selected library (and system scope as applicable) that counts items by material category with totals/subtotals. The reporting must include counts of items on shelf (checked in), items in circulation (checked out), newly acquired items, and holds counts (including holds associated with each reported category where applicable). The report must support configurable category groupings so libraries can use preferred category schemes (e.g., fiction/nonfiction or format-based groupings) and must support category breakdowns such as adult fiction and board books. This requirement covers current-state material volumes only (not historical snapshots or acquisition-period comparisons).

**Traced to:** `conversations/conv_pines014_material_volume.eml`, `early_draft_srs_galecia.txt`, `interview_cataloging_2009-05-08.txt`

### REQ-002: Material volume historical snapshots and acquisition-period reporting

**Priority:** Must

Allow material-volume reporting as of a specified point in time (historical snapshot) and support acquisitions during a selectable date period (e.g., last 30/60/90 days). Reports must support date filtering enabling historical comparisons and trend analysis. This requirement complements current material-volume reporting by adding time-travel (as-of) reporting and acquisition-period filtering; it should not duplicate current-state logic beyond what is necessary to interpret counts for historical dates.

**Traced to:** `conversations/conv_pines014_material_volume.eml`, `early_draft_srs_galecia.txt`

### REQ-003: Shelf-space and collection-distribution reporting with explicit shelf-space estimation

**Priority:** Must

Provide shelf-space usage reports that compare, for each genre and format, (a) percentage of total circulations, (b) percentage of the collection, and (c) estimated percentage of total shelf space. Results must be grouped by genre and format and runnable at both the individual-library level and system-aggregate level. Because shelf space is not directly tracked, the system must provide and document a shelf-space estimation approach (e.g., using item dimensions and/or a defined item-count proxy) and clearly state how the estimation maps item records to â€œestimated shelf-space units.â€

**Traced to:** `conversations/conv_pines016_shelf_space.eml`, `early_draft_srs_galecia.txt`, `interview_cataloging_2009-05-08.txt`

### REQ-004: Shelf-space utilization period comparison

**Priority:** Should

Support date-range filtering for shelf-space and related circulation measures so utilization can be compared across periods (e.g., calendar quarters). Provide a comparison view that displays each libraryâ€™s genre and format breakdown side-by-side to highlight differences and outliers. This requirement applies to filtering and comparative presentation; it does not re-specify the shelf-space estimation method (covered by REQ-003).

**Traced to:** `conversations/conv_pines016_shelf_space.eml`, `early_draft_srs_galecia.txt`

### REQ-005: Branch capacity overview interface (sorting, filtering, drill-down, export)

**Priority:** Must

Provide an interface that presents a high-level capacity overview for all branches and supports drill-down into capacity details for an individual branch. The interface must allow sorting (including by current load) and filtering (e.g., by region, library type, or current load) and must support export to CSV for spreadsheet use. This requirement focuses on the user interface behaviors and capabilities, not on defining the underlying capacity metric(s) (covered by REQ-006).

**Traced to:** `conversations/conv_pines015_capacity_interface.eml`, `early_draft_srs_galecia.txt`, `meeting_minutes/meeting_2009-03-15_minutes.txt`, `meeting_minutes/meeting_2009-07-20_minutes.txt`

### REQ-006: Capacity metric definition and alignment to displays

**Priority:** Must

Before implementing capacity displays and sorting, establish and document the metric(s) used to define branch capacity (examples include item counts, shelf-space units, configured maximums, circulation-processing capacity, or a defined composite measure). The requirement must explicitly describe how the chosen metric(s) relate to the capacity data presented in the interface, including which data sources are used and how â€œcurrent loadâ€ is calculated. The same metric definitions must be used consistently across the capacity overview interface and related calculations so results are actionable and non-ambiguous. This requirement covers metric definition and calculation semantics only (not UI behavior).

**Traced to:** `conversations/conv_pines015_capacity_interface.eml`, `early_draft_srs_galecia.txt`

### REQ-007: Branch capacity trend reporting for planning

**Priority:** Should

Provide trend data for branches indicating whether capacity or load is growing or shrinking over time to support long-term planning and distribution decisions. This requirement covers longitudinal trend reporting; it must not duplicate the capacity metric definition (REQ-006) or the UI interface capabilities (REQ-005).

**Traced to:** `conversations/conv_pines015_capacity_interface.eml`, `early_draft_srs_galecia.txt`

### REQ-008: Large-scale capacity usability (grouping/filtering and optional status color coding)

**Priority:** Should

Design the capacity overview to remain usable at consortium scale (e.g., ~286 branches) by supporting grouping (by system or region) and/or filtering to avoid overcrowding. Optionally, apply color coding (e.g., green/yellow/red) to indicate capacity status for at-a-glance comprehension. This requirement is about usability/visualization at scale, not about the metric definition or core reporting logic.

**Traced to:** `conversations/conv_pines015_capacity_interface.eml`, `meeting_minutes/meeting_2009-07-20_minutes.txt`

### REQ-009: Batch item-transfer utility across locations (query, preview, pull lists, labels, location updates)

**Priority:** Must

Provide a batch item-transfer utility that lets authorized users transfer groups of items between branches and other locations (including mobile libraries, outreach programs, warehouses, and temporary-event locations). The utility must support: querying catalog/item data to identify candidate materials; saving queries for repeated use (including recurring selection criteria); manual selection of items from query results; previewing proposed transfers (with counts, source, destination); generating pull lists for staff; updating item location fields to the destination; and producing printable transit labels where useful.

**Traced to:** `conversations/conv_pines018_item_transfer.eml`, `early_draft_srs_galecia.txt`, `interview_cataloging_2009-05-08.txt`

### REQ-010: Save/share transfer queries/templates with permissions governance

**Priority:** Must

Users must be able to save transfer queries for repeated use (e.g., monthly workflows). The system should support sharing saved queries or templates among staff or across branches according to permissions and template-sharing governance. This requirement complements REQ-009 by specifying persistence and governance aspects for saved transfer selection templates.

**Traced to:** `conversations/conv_pines018_item_transfer.eml`, `early_draft_srs_galecia.txt`, `interview_cataloging_2009-05-08.txt`

### REQ-011: Transaction-safe batch transfer processing with large-batch performance

**Priority:** Must

Batch transfer processing must be transaction-safe so partial failures do not leave inconsistent transfer records. It must also process large batches efficiently (e.g., by breaking updates into smaller batches to avoid excessive database locking) to scale for large consortia.

**Traced to:** `conversations/conv_pines018_item_transfer.eml`, `early_draft_srs_galecia.txt`

### REQ-012: Transfer reversion/undo (timed or criteria-based restoration)

**Priority:** Must

Support temporary transfers that preserve each itemâ€™s original location so items can be automatically reverted after a configured period (e.g., number of days or end of an event) or when configured criteria are met. Provide an explicit undo function to reverse erroneous transfers. Where practical, support event- or criteria-triggered reversion (e.g., when an item is returned or checked out at the destination).

**Traced to:** `conversations/conv_pines018_item_transfer.eml`, `early_draft_srs_galecia.txt`, `interview_cataloging_2009-05-08.txt`

### REQ-013: Transfer permissions, audit/history, and optional delay/issue alerts

**Priority:** Must

Restrict transfer capabilities to authorized roles (e.g., managers, administrators, or designated transfer coordinators). Maintain an audit log of all transfers for accountability and provide access to transfer history. The system should optionally notify designated users when transfers are delayed or encounter issues.

**Traced to:** `conversations/conv_pines018_item_transfer.eml`, `early_draft_srs_galecia.txt`

### REQ-014: Missing/damaged and in-transit item reporting (unified report with aging threshold)

**Priority:** Must

Provide branch-level reports of missing and damaged items and items in transit organized by branch and by system. Reports must identify relevant item statuses (including missing and lost) and include any available condition notes (e.g., water damage or vandalism). The system must provide a unified in-transit report that combines transit-to and transit-from items, and it must identify items in transit longer than a configurable threshold (default 7 days). The in-transit report must allow organization and sorting (e.g., by due date) to support prioritization. To avoid ambiguity, the requirement also includes that the system tracks these conditions via explicit item status/location fields (including an in-transit state and timestamps) and uses those stored status/location values to generate the reports.

**Traced to:** `conversations/conv_pines019_020_missing_intransit.eml`, `early_draft_srs_galecia.txt`, `interview_cataloging_2009-05-08.txt`

### REQ-015: Purge/weeding identification and safe deletion workflow (including last-copy handling)

**Priority:** Must

Provide utilities and read-only reports to identify item records eligible for purging using configurable criteria (including item statuses such as missing, discard/weed, and damaged; elapsed time in status; time since last circulation; and combinations of criteria). Present identified candidates read-only; require an explicit separate confirmation step for deletions. Support batch status conversions (e.g., many items from missing to discard/weed), last-copy reporting at library and system scope (flagging items that are the only copy in the selected scope), and efficient deletion of volume entries together with their copy entries and of records with no attached items.

**Traced to:** `conversations/conv_pines021_item_purging.eml`, `early_draft_srs_galecia.txt`, `interview_cataloging_2009-05-08.txt`

### REQ-016: Deletion audit store and deletion-activity reporting (including denied attempts)

**Priority:** Must

Log every completed deletion in a persistent audit store capturing at minimum record type, record identifier, deletion timestamp, user who performed the deletion, and the userâ€™s location or branch. Provide reporting interfaces to query deletion audit data by location, system, date range, and record type (including item, patron, and bibliographic records). Capture and make available denied-deletion attempts for review.

**Traced to:** `conversations/conv_pines022_deletions.eml`, `early_draft_srs_galecia.txt`, `interview_cataloging_2009-05-08.txt`

### REQ-017: Patron characteristics segmentation reporting

**Priority:** Must

Support patron queries and reports that use age range (computed from birth date at query time), ZIP code, county of residence, home branch, patron type, and preferred language as selection dimensions. Allow grouping/aggregation by these characteristics, include patrons with missing optional fields represented as null, and allow combining multiple demographic filters using AND and OR logic. Age brackets used in reports must be configurable.

**Traced to:** `conversations/conv_pines023_patron_characteristics.eml`, `early_draft_srs_galecia.txt`, `survey_results_2009.txt`

### REQ-018: Inactive-patron reporting and outreach export with electronic activity rules

**Priority:** Must

Generate configurable reports of patrons with no circulation or electronic activity during a configurable number of days (threshold must accept arbitrary day values). Electronic activity used for inactivity determination must be precisely defined and tracked via stored events/logs, including OPAC/patron-account logins, online hold placements, and online item renewals; it must also include integrated digital-resource access events when patrons are authenticated. Reports must support scoping/grouping by System, Home Library, County, or similar levels; include current mailing addresses for outreach; separate patrons with outstanding fines for distinct handling; allow exclusion of designated patron categories (e.g., do-not-disturb, VIP, staff, communication opt-out); export results as CSV for upload to outreach systems; run as background processes; and optionally cache results to improve performance.

**Traced to:** `conversations/conv_pines024_inactive_patrons.eml`, `early_draft_srs_galecia.txt`, `survey_results_2009.txt`

### REQ-019: Reporting platform query builder, templates, cloning, and fine-grained permissions

**Priority:** Must

Provide a user-friendly query-builder interface covering bibliographic, item, patron, transaction, and financial records. It must allow field selection, picklist values, regular-expression options via dropdown, and full Boolean operators. Administrators must be able to create, publish, and migrate report templates; templates must execute consistently so users running the same named report use the same criteria unless changes are permitted. Administrators must restrict which filters and display fields may be altered. Support cloning of templates, saving and sharing queries, fine-grained report permissions (separately controlling who may create, clone, run, or modify reports), and role-based permission administration that updates automatically when a user's role changes.

**Traced to:** `early_draft_srs_galecia.txt`, `email_report_features.eml`, `evergreen_reference_2009.txt`, `meeting_tech_subcommittee_2009-06-30.txt`, `survey_results_2009.txt`

### REQ-020: Report execution scheduling/queue management with status, priority, and cancellation

**Priority:** Must

Support immediate and scheduled/recurring report execution (Run ASAP; hourly, daily, weekly, monthly, yearly) and allow multiple canned reports to run together. Long-running or resource-intensive reports must execute as background processes or via a reporting queue. Staff must be able to view a reportâ€™s queue position, submission timestamp, and processing status (waiting, running, completed, failed). Allow prioritizing selected reports so critical reports run ahead of lower-priority ad hoc queries, and allow authorized users to cancel scheduled or running reports.

**Traced to:** `early_draft_srs_galecia.txt`, `email_report_features.eml`, `evergreen_reference_2009.txt`, `interview_sysadmin_2009-05-10.txt`, `meeting_tech_subcommittee_2009-06-30.txt`, `survey_results_2009.txt`

### REQ-021: Report output formats, delivery mechanisms, and transparency of selection criteria

**Priority:** Must

Support export and delivery in standard formats: CSV and HTML are required; Excel support where applicable and pivot-table output where useful. Scheduled reports must be deliverable by email (optionally via an address book). Report outputs must include the report name and the selection criteria (query selections and date criteria) alongside results to ensure transparency and reproducibility.

**Traced to:** `early_draft_srs_galecia.txt`, `email_report_features.eml`, `evergreen_reference_2009.txt`, `meeting_tech_subcommittee_2009-06-30.txt`, `survey_results_2009.txt`

### REQ-022: Reporting data architecture separating production operations from reporting

**Priority:** Must

Isolate reporting from production operations by providing a separate reporting database or replica. Support both real-time reporting against current data and historical reporting via a reporting warehouse capable of producing historical snapshots (e.g., values as of a past date or bills as they existed at a prior point in time). The architecture must include a technical approach for achieving isolation (e.g., read-replication and/or ETL pipelines with reporting-schema separation) and must support consortium-scale workloads (e.g., hundreds of branches and millions of annual circulations) without disrupting operational services.

**Traced to:** `early_draft_srs_galecia.txt`, `evergreen_reference_2009.txt`, `interview_sysadmin_2009-05-10.txt`, `meeting_minutes/meeting_2009-07-20_minutes.txt`, `meeting_tech_subcommittee_2009-06-30.txt`, `survey_results_2009.txt`

### REQ-023: Accessibility and standards-compliant web interfaces (Section 508 focus and legacy browser definition)

**Priority:** Must

Ensure reporting and management interfaces are accessible (Section 508 compliance and support for screen readers such as JAWS and NVDA, screen magnification tools such as ZoomText, and other assistive technologies). Produce standards-compliant, semantic HTML with ARIA, alt text, and proper structure. Support legacy browser compatibility where required by defining legacy browsers as Microsoft Internet Explorer 6.0+ and Firefox 2.0+ when a web client is used. Provide online hierarchical, cross-linked HTML help that is accessible and preferably searchable.

**Traced to:** `early_draft_srs_galecia.txt`, `interview_sysadmin_2009-05-10.txt`, `meeting_minutes/meeting_2009-07-20_minutes.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

### REQ-024: Transaction retention, classification, and anonymized reporting for compliance

**Priority:** Must

Retain detailed transaction history for a configurable number of days while retaining monthly and annual aggregates indefinitely. Classify and count transactions by operational dimensions (hour, terminal, branch, system, transaction type and channel). Separately report check-in and renewal timestamps. Archive transaction data in a way that preserves the ability to produce demographic statistics while anonymizing or removing personally identifiable information to comply with applicable law. The requirement must include specific anonymization controls (e.g., removal/obfuscation of direct identifiers and retention of only values needed for demographic reporting, plus access control for any sensitive fields) so compliance is measurable.

**Traced to:** `early_draft_srs_galecia.txt`, `email_report_features.eml`, `survey_results_2009.txt`

### REQ-025: Comprehensive financial reporting with payment ledger and accounting/auditing compliance

**Priority:** Must

Provide comprehensive financial reporting including item-value reports (using purchase price or other item-record value), patron account balances (by patron, home library, and system), fines/charges by selectable periods and charge types, waived-fines reporting by period and branch, and payments reporting by period, payment method, and collection channel. Maintain a payment audit ledger recording which payments were applied to which charges, ensure financial data (fines, charges, waivers, payments, ecommerce transactions) is associated with patron and item records, support querying accounts above a specified balance threshold, and ensure front-desk payments update system balances immediately. Financial reporting and archiving must comply with standard accounting practices and applicable auditing and retention requirements; the requirement must explicitly state which accounting standards/audit framework(s) apply to the consortium so compliance can be verified (e.g., specified retention duration, audit trail requirements).

**Traced to:** `early_draft_srs_galecia.txt`, `email_financial_reports.eml`, `meeting_minutes/meeting_2009-03-15_minutes.txt`

### REQ-026: Data-quality reporting and cataloging support workflows (including prioritization/remediation process)

**Priority:** Must

Provide data-quality reports that identify cataloging and item-data issues (e.g., invalid item types, excessively long call numbers, bibliographic records with no attached item records). Expose last-edit dates separately from last-circulation dates and ensure check-in and renewal timestamps are distinct. Supply workflows and reports (including last-copy reporting at library and system scope) to help catalogers review and clean up orphaned records or last-copy deletions safely. Also support tracking and lightweight inventory control for uncataloged materials and include uncataloged-material transactions in circulation statistics. Additionally, include a process to prioritize identified data-quality issues and to drive remediation through defined workflows (e.g., severity scoring and assignment/queueing for follow-up) so findings are actionable rather than purely informational.

**Traced to:** `conversations/conv_pines016_shelf_space.eml`, `evergreen_reference_2009.txt`, `interview_cataloging_2009-05-08.txt`

### REQ-027: Report discovery/usability with integrated help

**Priority:** Should

Make reports easier to find and use via discoverable navigation, quick-access interfaces, pop-up descriptions and hover tooltips for report titles, and integrated online help. Provide searchable help content so staff can learn how to run and interpret reports without routine IT assistance.

**Traced to:** `evergreen_reference_2009.txt`, `meeting_tech_subcommittee_2009-06-30.txt`, `survey_results_2009.txt`

### REQ-028: Reports development governance: testing group review and executive/library templates

**Priority:** Must

Subject all new report development to review and testing by the designated Reports testing group before acceptance. Provide an Executive Reports Interface and predefined board/executive report templates plus a set of library report templates for the consortium. Support an iterative, prototype-oriented development process that gives end users multiple review opportunities, particularly for UI and data-structure behavior.

**Traced to:** `meeting_minutes/meeting_2009-03-15_minutes.txt`, `meeting_minutes/meeting_2009-07-20_minutes.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

### REQ-029: Platform compatibility and operational non-disruption during open hours

**Priority:** Must

The reporting and management system must operate on supported server environments (Linux and Solaris; existing environments include Red Hat Enterprise Linux 5 and Solaris 10 on SPARC) and be compatible with the existing relational database environment (PostgreSQL compatibility required where applicable). Searches and reports must be processable during open hours without disrupting other system functions, including OPAC responsiveness and circulation operations.

**Traced to:** `early_draft_srs_galecia.txt`, `interview_sysadmin_2009-05-10.txt`, `meeting_minutes/meeting_2009-07-20_minutes.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

## Discarded or conflicting candidates

### DISCARD-001

Keep REQ-001 and REQ-002 as separate, but allow overlap/unclear distinction between current-state vs historical/acquisition-period material-volume logic.

**Reason:** Rejected because the audit found these were related but complementary; the consolidated requirements explicitly separate â€œcurrent-state reportingâ€ from â€œhistorical snapshot/acquisition-period reportingâ€ to prevent overlap ambiguity.

**Sources:** `conversations/conv_pines014_material_volume.eml`, `early_draft_srs_galecia.txt`

### DISCARD-002

Keep REQ-005 and REQ-006 without clarifying that REQ-006 defines metrics while REQ-005 specifies interface behaviors.

**Reason:** Rejected to address the auditâ€™s redundancy/clarity issue; the consolidated set preserves both but clearly delineates metric semantics (REQ-006) from UI sorting/filtering/drill-down/export (REQ-005).

**Sources:** `conversations/conv_pines015_capacity_interface.eml`, `early_draft_srs_galecia.txt`

### DISCARD-003

Keep REQ-007 and REQ-008 overlapping the same capacity capability space (trend vs usability) without differentiation.

**Reason:** Rejected because the audit requested functional differentiation; the consolidated requirements state trend reporting (REQ-007) vs usability/visualization at scale (REQ-008).

**Sources:** `conversations/conv_pines015_capacity_interface.eml`, `meeting_minutes/meeting_2009-07-20_minutes.txt`, `early_draft_srs_galecia.txt`

### DISCARD-004

Keep REQ-014 without specifying how missing/damaged/in-transit tracking is represented in stored item status/location/timestamps.

**Reason:** Rejected because REQ-014â€™s audit gap could cause ambiguity; the consolidated requirement adds that reports are derived from explicit tracked statuses and in-transit timestamps.

**Sources:** `conversations/conv_pines019_020_missing_intransit.eml`, `interview_cataloging_2009-05-08.txt`

### DISCARD-005

Keep REQ-018â€™s 'electronic activity rules' vague (no explicit tracking definitions for logins/holds/renewals/digital-resource access).

**Reason:** Rejected to address the audit; the consolidated requirement specifies what constitutes electronic activity and that it is tracked via stored events/logs for inactivity determination.

**Sources:** `conversations/conv_pines024_inactive_patrons.eml`, `survey_results_2009.txt`

### DISCARD-006

Keep REQ-022 without specifying a technical approach to isolate production from reporting (e.g., replication vs ETL), only stating 'separate database or replica'.

**Reason:** Rejected because the audit required architectural clarity; the consolidated requirement adds that isolation must be achieved via an explicit technical approach (e.g., replication/ETL and reporting-schema separation).

**Sources:** `interview_sysadmin_2009-05-10.txt`, `meeting_minutes/meeting_2009-07-20_minutes.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

### DISCARD-007

Keep REQ-023 without defining which browsers count as 'legacy'.

**Reason:** Rejected because the audit requested a clear definition; the consolidated requirement defines legacy browsers as IE 6.0+ and Firefox 2.0+ when a web client is used.

**Sources:** `interview_sysadmin_2009-05-10.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

### DISCARD-008

Keep REQ-024 without specifying how anonymization is implemented (types of identifiers removed/obfuscated and access controls).

**Reason:** Rejected because the audit noted missing implementation specifics; the consolidated requirement includes measurable anonymization controls and access control expectations.

**Sources:** `email_report_features.eml`, `survey_results_2009.txt`, `early_draft_srs_galecia.txt`

### DISCARD-009

Keep REQ-025 without stating which accounting standards/audit framework applies (only generic 'standard accounting practices').

**Reason:** Rejected because the audit asked for measurable standards; the consolidated requirement requires explicit standards/framework selection for verification.

**Sources:** `email_financial_reports.eml`, `meeting_minutes/meeting_2009-03-15_minutes.txt`

### DISCARD-010

Keep REQ-026 without a remediation/prioritization process (data-quality reports only, no workflow to address issues).

**Reason:** Rejected because the audit asked for an actionable remediation process; the consolidated requirement adds prioritization and workflow-driven remediation expectations.

**Sources:** `evergreen_reference_2009.txt`, `interview_cataloging_2009-05-08.txt`, `conversations/conv_pines016_shelf_space.eml`

