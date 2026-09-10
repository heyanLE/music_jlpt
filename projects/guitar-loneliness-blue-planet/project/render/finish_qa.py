"""Record actual visual inspection and verified technical evidence before promotion."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'project';QA=P/'qa/render-r1'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    report=load(QA/'qa-report.json');tech=load(QA/'custom-technical-report.json')
    assert tech['status']=='passed-technical-pending-visual'
    assert report['candidateSha256']==tech['candidateSha256']
    assert hashlib.sha256((ROOT/report['candidate']).read_bytes()).hexdigest()==report['candidateSha256']
    report['result']='passed'
    report['technicalReport']='project/qa/render-r1/custom-technical-report.json'
    report['validationRoute']='Common render gate + custom packet/PCM/timing/spectrum checks; generic render validator not used for unsupported custom preset.'
    report['visualInspection']={
        'inspected':['contact-sheet.jpg','countdown-2.png','loanword.png','transition-gaussian-cover.png','mixed-language.png'],
        'findings':[
            'Background retains original 16:9 aspect ratio. Selected source begins at 16 seconds; subsequent Gaussian segment fades only its background.',
            'Normal 220 px top-center cover, bold outlined text, pink active highlight and semi-transparent pink cards match the reviewed static template.',
            '3/2/1 badge visible separately; disappears at the first sung unit. First glyph, whole token ruby and romaji highlight together; cards stay unhighlighted.',
            'Static adjacent lyrics appear on the same baselines at true canvas edges. No sliding animation or inset clipping boundary.',
            'Follow-mode gap hides the study foreground while spectrum stays visible; Gaussian transition and tail retain the foreground.',
            'Elixir source annotation present. Numeric Japanese 300mm includes its accepted romaji; this is not an English phrase. No pure English lyric requires separate handling in this song.',
            'Meanings are concise, labels use 动词 instead of conjugation class. All cards remain one row; dense 300mm row has no romaji overlap.',
            'Spectrum is visible at the bottom without a black rectangle. Eight paired original-overlay frame checks establish motion across intro, song, transition and tail sections.'
        ],
        'limitations':['Original source video includes promotional lettering and its ending artwork; these were retained as requested footage.','Later TV-short performance arrangement differs from full studio audio, as disclosed during alignment review.','Audio sample/clock matching is mechanically verified; no claim of full perceptual listening or device-specific playback testing.']
    }
    write(QA/'qa-report.json',report)
    state=load(P/'build-state.json');state['stage']='qa_passed';state['evidence']['finalQa']='project/qa/render-r1/qa-report.json';state['nextAction']='Promote the checked candidate into deliverables/final.';write(P/'build-state.json',state)
    original=ROOT/'deliverables/review/智能复审-待采纳.md'
    text=original.read_text(encoding='utf-8').replace('— 多角色审核提案','— 已确认词卡',1).replace('状态：尚未采纳。原始 frames.json 未修改；以下为 48 句的拟采用内容，可直接在本 Markdown 修改。','状态：用户已确认（“确认，需要频谱动画”）。以下内容已合并到活动 frames.json 并用于 render-r1；再编辑后需差异导入和重新渲染。',1).replace('## 优先核对','## 审查记录（随当前版本确认）',1)
    target=ROOT/'deliverables/review/词卡-已确认.md';target.write_text(text,encoding='utf-8')
    write(P/'review/confirmed-markdown-baseline.json',{'file':target.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'frameSha256':hashlib.sha256((P/'frames.json').read_bytes()).hexdigest()})
    print('QA passed; confirmed review Markdown exported.')
if __name__=='__main__':main()
