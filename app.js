const $ = (selector) => document.querySelector(selector);
const note = $('#record-note');
const row = $('#added-row');
const result = $('#lab-result');
const original = [{ id: 'R-101', name: 'North Studio' }, { id: 'R-102', name: 'River Workshop' }];
export function mergeRecords(incoming, saved) {
  const ids = new Set();
  for (const record of incoming) {
    if (!record.id || ids.has(record.id)) throw new Error('Duplicate or missing record ID. Refresh stopped; existing notes were not changed.');
    ids.add(record.id);
  }
  if (Object.keys(saved).some((id) => !ids.has(id))) throw new Error('Refresh would remove a tracked record. Existing notes were not changed.');
  return incoming.map(record => ({...record, note: saved[record.id] ?? ''}));
}
$('#refresh-demo')?.addEventListener('click', () => {
  const merged = mergeRecords([...original, { id: 'R-103', name: 'New source record' }], { 'R-101': note.value, 'R-102': 'Review import' });
  row.hidden = false; result.classList.remove('error');
  result.textContent = 'Refresh complete: 3 records. R-101 kept your note: “' + merged[0].note + '”.';
});
$('#duplicate-demo')?.addEventListener('click', () => {
  try { mergeRecords([original[0], original[0]], { 'R-101': note.value, 'R-102': 'Review import' }); }
  catch (error) { result.classList.add('error'); result.textContent = error.message; }
});
$('#reset-demo')?.addEventListener('click', () => {
  note.value = 'Keep this note'; row.hidden = true; result.classList.remove('error');
  result.textContent = 'Edit the note, then refresh. Its record ID keeps it attached.';
});
$('#copy-email')?.addEventListener('click', async () => {
  const status = $('#copy-status');
  try { await navigator.clipboard.writeText('nordiccompany0@gmail.com'); status.textContent = 'Email address copied.'; }
  catch { status.textContent = 'Copy is unavailable. Select the email address above, or use its email link.'; }
});
$('#brief-form')?.addEventListener('submit', (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  if (!form.reportValidity()) return;
  const fields = new FormData(form);
  const problem = String(fields.get('problem') ?? '').trim();
  if (!problem) { $('#brief-status').textContent = 'Please describe the problem first.'; $('#brief-problem').focus(); return; }
  const body = ['Hello Ivan,', '', 'Project / problem:', problem, '', 'Technical context or public link:', String(fields.get('context') || 'Not yet provided'), '', 'Indicative budget:', String(fields.get('budget') || 'To discuss'), '', 'I would like to clarify the deliverable, acceptance checks and protected payment arrangement before agreeing on timing.'].join('\n');
  const link = $('#prepared-email');
  link.href = 'mailto:nordiccompany0@gmail.com?subject=' + encodeURIComponent('Technical project inquiry') + '&body=' + encodeURIComponent(body);
  link.hidden = false;
  $('#brief-status').textContent = 'Draft ready. Use the link below to open your email app; review and send it there. Nothing has been sent by this website.';
});

$('#brief-form')?.addEventListener('input',()=>{ $('#prepared-email').hidden=true; $('#brief-status').textContent=''; });
