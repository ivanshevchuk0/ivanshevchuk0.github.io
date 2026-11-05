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
