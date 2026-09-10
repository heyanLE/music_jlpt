"""Finalize the opening-only revision after inspecting its actual output samples."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'project';QA=P/'qa/render-r2-countdown'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    report=load(QA/'qa-report.json');tech=load(QA/'custom-technical-report.json');reveal=load(P/'qa/countdown-reveal-check.json')
    assert tech['status']=='passed-technical-pending-visual' and reveal['status']=='passed'
    assert report['candidateSha256']==tech['candidateSha256']==hashlib.sha256((ROOT/report['candidate']).read_bytes()).hexdigest()
    report['result']='passed'
    report['technicalReport']='project/qa/render-r2-countdown/custom-technical-report.json'
    report['revisionCheck']='project/qa/countdown-reveal-check.json'
    report['validationRoute']='Common gate and explicit custom technical/timeline/visual checks; no unsupported generic render validator claim.'
    report['visualInspection']={'inspected':['prelude.png','before-first-reveal.png','first-reveal.png','countdown-2.png','countdown-end.png','contact-sheet.jpg'],'findings':['Before 33.050 s, background and transparent spectrum remain; no study cover, lyrics, translation, cards or foreground veil.','At 33.050 s first complete study foreground and countdown 3 appear together. 2/1 and first singing then retain the original timestamps.','Following lyric gaps, Gaussian scene transition, adjacent lines, card layout and highlights remain as in the approved R1 render.','Spectrum remains at video bottom through the opening visibility change and is independently verified as byte-identical to R1.','Output audio PCM matches the same lossless program, and original master suffix remains bit-exact.'],'limitations':['Source TV-short arrangement differs from full master later, as previously disclosed.','Original footage promotional lettering is retained.']}
    write(QA/'qa-report.json',report)
    state=load(P/'build-state.json');state['stage']='qa_passed';state['evidence']['finalQa']='project/qa/render-r2-countdown/qa-report.json';state['evidence']['countdownReveal']='project/qa/countdown-reveal-check.json';state['notes'].append('Opening-only revision: no study foreground before 33.050 s, first study frame revealed with countdown 3; all later timeline states unchanged.');write(P/'build-state.json',state)
    print('Opening-only revision QA passed.')
if __name__=='__main__':main()
