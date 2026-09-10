"""Human review in the confirmed dare-v3 card format, without accepting proposals."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'project'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def cardline(c): return '｜'.join([c['token'],c['reading'],c['romaji'],c.get('functionZh',c.get('zhMeaning','')),c['grammarStructureZh']])
def main():
    base=load(P/'frames.json'); proposed=load(P/'review/round2-integrated-proposed-frames.json'); report=load(P/'review/round2-integration-report.json')
    before={f['id']:f for f in base['frames']}
    explanations={
        'l009':'よく言ったもの是评价这个说法贴切，不能按常说或只需照做来解释；整句源译问题另列。',
        'l011':'今日按本曲QQ文本保留こんにち，卡义按上下文取如今；変わらない可修饰下一句この空欄，因此保留没有改变并将句法解释放这里。',
        'l012':'解ける存在词典自动词与解く可能形同形；保留当前自动词分析作为可行读法，不宣称排除了另一分析。',
        'l023':'であって在这里是断定身份的中顿，不是表示作为某种身份去做事。',
        'l029':'拆分样态与程度：溢れだしそうな／ほど／詰め込んだ。末项连体修饰下一句他人の箱，不补写是谁把箱子塞满。',
        'l030':'承接上一句，箱子属于别人；横目に采用中性的瞥着，不额外添轻蔑、嫉妒。',
        'l031':'下手（へた）补熟字训说明；只标汉字下手，正文な不重复注音。',
        'l032':'出来てない补动词身份，并明确为ていない省略い的口语形式。',
        'l035':'拆成このままで／いい／なんて：状态、评价、引用分别对应。后句否定这种想法，本句不是作者独立提出的建议。',
        'l038':'与下一句のか共同列出选项，受分からない支配，按间接疑问解释。',
        'l041':'なんだ已正确表示算什么的反问，保留原卡；QQ整句是什么可能弱化此语气，另列待审。',
        'l043':'身份解读符合上下文，但原卡若不是我自己／无法活下去已能表达该范围，未强换成更具体的扮演他人说法。'
    }
    intro=['# 空の箱｜第二轮多角色词卡复审（待采纳）','','按 dare-v3 最新已确认稿的格式列出完整词卡。上一轮提案不作为已接受内容；以下为重新审查后的建议，正式 frames.json 未改。','','词卡格式：**词条｜读音｜罗马音｜中文含义／助词功能｜词性与必要结构**。','','粗体词卡＝建议修改；普通词卡＝复查后建议保留。QQ 整句中文仍是原翻译轨，可能与日文跨行调序，不能逐行硬对应。','',f"范围：45 句；原 {report['counts']['cardsBefore']} 卡，建议 {report['counts']['cardsProposed']} 卡。",'']
    full=intro.copy(); changes=['# 空の箱｜第二轮需要修改的词卡','','只列改变的词卡及所在句中文；完整逐句稿见 kara-no-hako-round2-review.md。均为未采纳建议，QQ 中文不在本次词卡批量修改范围。','']
    for f in proposed['frames']:
        old=before[f['id']]; oldlines=[cardline(c) for c in old['grammarCards']]; newlines=[cardline(c) for c in f['grammarCards']]
        full += [f"## {f['id']}  {f['caption']['japanese']}",'',f"- 整句中文（QQ）：{f['caption']['translationZh']}",'- 词卡：']
        for index,line in enumerate(newlines):
            changed=line not in oldlines
            full.append('  - '+('**'+line+'**' if changed else line))
        if f['id'] in explanations: full += ['', '审核说明：'+explanations[f['id']]]
        if oldlines!=newlines:
            changes += [f"## {f['id']}  {f['caption']['japanese']}",'',f"整句中文（QQ）：{f['caption']['translationZh']}",'','原词卡：','']
            changes.extend('- '+s for s in oldlines if s not in newlines)
            changes += ['','建议词卡：','']
            changes.extend('- '+s for s in newlines if s not in oldlines)
            if f['id'] in explanations: changes += ['', '审核说明：'+explanations[f['id']]]
            changes.append('')
        full.append('')
    notes=['## 保留的判断与审核边界','','- 今日：按当前 QQ 假名／罗马音保留「こんにち / konnichi」；未独立听辨，不改成另一首歌的「きょう」。','- 明日：保留「あした / ashita」并标熟字训；其他难字不一概贴熟字训标签。','- コタエ、カタチ是和语的片假名写法，不补虚构的英语词源。','- 纯助词使用功能；固定短语整体给含义；不把完整语法块全部拆碎。','- 原歌词、QRC 时间、整句中文、前景模板、下一句预读、背景和音频均未修改。','- 采纳词卡建议后仍需另行授权最终视频渲染。','', '证据与逐句检查记录：','', '- [词汇角色](../../project/proposals/round2/lexical.json)','- [文法角色](../../project/proposals/round2/grammar.json)','- [翻译角色](../../project/proposals/round2/translation.json)','- [整合决定](../../project/review/round2-integration-report.json)','']
    notes += ['[QQ整句译文的7组单独待审建议](kara-no-hako-round2-source-translations.md)：仅供另行决定，不混入词卡采纳范围。','', '本轮没有把全部同义词删减或罗马音空格调整列为必改。其排除理由均留在整合报告中。','']
    full+=notes; changes+=notes
    for name,lines in [('kara-no-hako-round2-review.md',full),('kara-no-hako-round2-changes.md',changes)]:
        (ROOT/'deliverables/review'/name).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    trans=load(P/'proposals/round2/translation.json')
    sources={s['id']:s for s in trans.get('sources',[])}
    source_doc=['# 空の箱｜QQ整句中文单独待审','','以下7组是源译疑点，不改动QRC、时码或正式中文。学习参考中跨行合并是为了说明句意，并非提出合并显示帧；即使采纳全部词卡，也不会自动采纳本文件。','']
    for issue in trans['sourceTranslationIssues']:
        source_doc += ['## '+' / '.join(issue['frameIds']),'']
        for item in issue['sourceValues']:
            fid=item['frameId'];source_doc += [f"{fid}　{before[fid]['caption']['japanese']}",'',f"QQ原文：{item['translationZh']}",'']
        source_doc += ['学习参考（未采纳）：'+issue['suggestedCombinedTranslation'],'','原因：'+issue['explanation'],'']
        for ref in issue.get('evidence',[]):
            if ref in sources:
                s=sources[ref]
                if s.get('url'): source_doc += [f"参考：[{s.get('title',ref)}]({s['url']})",'']
    (ROOT/'deliverables/review/kara-no-hako-round2-source-translations.md').write_text('\n'.join(source_doc)+'\n',encoding='utf-8')
    print(json.dumps(report['counts'],ensure_ascii=False))
if __name__=='__main__':main()
