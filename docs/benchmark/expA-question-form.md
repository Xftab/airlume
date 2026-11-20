# Experiment A: question collection form (English and Roman Urdu)

Text for a Google Form, to collect the held-out main set for Experiment A (protocol section
6.1). Make the form in Google Forms by hand from this text; collect no names, emails or phone
numbers. Turn off "Collect email addresses" and "Limit to 1 response" (that setting needs a
sign-in).

Do not show contributors the app or any example answers before they write, and give no example
questions: examples pull people towards questions the form can already answer, which is the
bias this experiment must avoid.

[UMT ethics requirement for an anonymous question survey: confirm with Dr Rimsha before sharing
the link.] [Contact email for the form: fill in.]

---

## Form title

Ask about the air / Hawa ke baare mein poochein

## Description (shown at the top)

**English.** We are three final-year BS Data Science students at the University of Management
and Technology, Lahore (supervisor: Dr Rimsha Anam). We are testing a computer assistant that
answers questions about air quality (smog, AQI, PM2.5) in Lahore and other cities of Pakistan.
We need real questions, written the way people actually type them.

Please write up to five questions you would want to ask about the air. Write in English, Roman
Urdu (Urdu in English letters) or a mix, exactly as you would type to a friend or a chatbot.
Spelling does not matter. Do not use a chatbot or AI tool to write them.

We collect only your questions. Do not write your name, phone number, address or anything that
identifies you or anyone else. Your questions may be published in a research dataset without
any name. Taking part is voluntary. It takes about 3 minutes. Contact: [email].

**Roman Urdu.** Hum University of Management and Technology, Lahore ke BS Data Science ke
final year ke teen students hain (supervisor: Dr Rimsha Anam). Hum ek computer assistant test
kar rahe hain jo Lahore aur Pakistan ke doosre shehron mein hawa ke mayaar (smog, AQI, PM2.5)
ke baare mein sawalon ke jawab deta hai. Humein asli sawal chahiyein, bilkul waise jaise log
type karte hain.

Hawa ke baare mein zyada se zyada paanch sawal likhein jo aap poochna chahenge. English, Roman
Urdu ya dono mila kar likhein, bilkul waise jaise aap kisi dost ya chatbot ko type karte hain.
Spelling ki fikr na karein. Sawal likhne ke liye koi chatbot ya AI tool istemal na karein.

Hum sirf aap ke sawal jama karte hain. Apna naam, phone number, pata ya koi aisi baat na likhein
jis se aap ya koi aur pehchana jaye. Aap ke sawal naam ke baghair research dataset mein shaya ho
sakte hain. Hissa lena aap ki marzi hai. Is mein taqreeban 3 minute lagte hain. Rabta: [email].

## Section 1: consent (required)

**Checkbox, required.**
I am 18 or older and I agree that my questions may be used and published without my name. /
Meri umar 18 saal ya us se zyada hai aur main raazi hoon ke mere sawal mere naam ke baghair
istemal aur shaya kiye ja sakte hain.

## Section 2: your questions

Five "Short answer" fields, only the first required:

- Question 1 / Sawal 1 (required)
- Question 2 / Sawal 2
- Question 3 / Sawal 3
- Question 4 / Sawal 4
- Question 5 / Sawal 5

Help text under each field: Any question about air quality: now, a past day, a comparison, a
forecast, what to do, anything. / Hawa ke mayaar ke baare mein koi bhi sawal.

## Section 3: about you (optional, nothing identifying)

- **Which language did you mostly write in? / Aap ne zyada tar kis zabaan mein likha?**
  English / Roman Urdu / Both, mixed / Urdu script / Other
- **Do you live in Lahore? / Kya aap Lahore mein rehte hain?** Yes / No / Prefer not to say
- **Are you a student? / Kya aap student hain?** Yes, at UMT / Yes, elsewhere / No / Prefer not to say

## After the form closes: intake rules (team only)

1. Export the responses. Copy every question, unchanged (spelling, case and punctuation kept;
   only leading and trailing spaces removed), into a copy of
   `airlume/eval/expA/intake-template.csv`, one row per question.
2. Drop, with the reason written in `drop_reason`: anything with personal details (name, phone,
   address); exact duplicates (keep the first); text that is not a question or request; abuse.
   Keep incomplete or misspelled questions: users send those too.
3. A team member who wrote a question cannot annotate it. Record which questions came from team
   members, if any, so they can be excluded or reported separately.
4. For each kept question, a second team member who speaks both languages writes the other
   language's version (English for a Roman Urdu question and the reverse); a third checks it
   reads naturally. Both versions get the same pair id.
5. Give ids (`xa-0001` onwards) and write the item file (format in `airlume/eval/expA/items.py`);
   run `python scripts\expA_run.py check --items <file>`.
6. Report how many responses, questions kept, questions dropped by reason, and the language mix.
