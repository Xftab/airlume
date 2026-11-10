# Can the raw EPA archive stay in a public repository? Options and a recommendation

**Date:** 6 November 2026. **Author:** Claude. **Status:** recommendation. The decision, and any message to the EPA, is Aftab's.

## The question

On 4 Nov the Punjab EPA said yes to *using* its data, through Dr Rimsha Anam, and no to supplying more. The wording has not yet been pasted into HISTORY. Meanwhile the repository `Xftab/airlume` is **public** and holds the raw hourly station archive (`data/archive/readings/punjab_epa/`, 3,294 station-hours so far). Publishing that archive is redistribution, which is a step beyond use. The plan already says "Raw EPA readings are released only if permission was granted" (plan, licensing), so the open point is whether "use" covers it.

## Options

| Option | What it takes | Cost and risk |
|---|---|---|
| **A. Ask one precise question** through the supervisor: "May the hourly readings we collected from aqi.punjab.gov.pk be published, with attribution, in the project's open-source repository?" | One email | None. It settles the question either way |
| **B. Keep public until the wording is seen** | Nothing | If the answer turns out to be "use only", the archive has been redistributed for weeks, and git history keeps it even after deletion |
| **C. Make the repository private** | Repository settings, by Aftab | GitHub Free includes 2,000 Actions minutes a month for private repositories; public ones are free. The cloud collector runs up to three times an hour (cron at :17 and :47, plus the cron-job.org dispatch): about 2,160 one-minute runs a month, **over the free allowance**. The two `schedule:` lines in `.github/workflows/collect.yml` would have to go first, keeping the hourly dispatch (about 720 minutes). Whether Streamlit Community Cloud serves a public app from a private repository must be checked in its console. |
| **D. Split the data out** into a second, private repository | Restructure the collectors and the app's data loading | Most work, most moving parts, three weeks before submission. Not recommended |

## Recommendation

1. **Do A now.** It costs one email, and the reply will also give the date and wording HISTORY still needs. The question is drafted above, so Dr Rimsha can forward it as it stands.
2. **Until the answer arrives, keep B, but do not deploy the app publicly.** The app shows EPA readings with attribution, which is use, so the deploy is safe once the repository question is settled. It is safer still to wait the few days.
3. **If the answer is "use only", or there is no answer by about 12 Nov (Week 3 deploy)**, do C:
   - remove the two cron lines from `collect.yml` (a file only Aftab can edit);
   - then make the repository private;
   - then deploy.
   The derived statistics (W1, CAMS validation, forecasts) can still be published in the report, as the plan already allows.
4. **Whatever happens, the report states which of these was done and when.**

## Sources

- [GitHub's plans: Actions minutes for GitHub Free](https://docs.github.com/en/enterprise-server@3.17/get-started/learning-about-github/githubs-plans): 2,000 minutes a month, and free for public repositories.
- [Streamlit: deploy a private app for free](https://blog.streamlit.io/deploy-a-private-app-for-free): private deployment exists, but the page does not say whether a public app can come from a private repository.
