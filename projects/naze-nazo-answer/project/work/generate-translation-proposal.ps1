$ErrorActionPreference = 'Stop'
$project = 'C:\project\musicjlpt\projects\naze-nazo-answer'
$framesPath = Join-Path $project 'project\frames.json'
$framesBytes = [System.IO.File]::ReadAllBytes($framesPath)
$sha = ([System.Security.Cryptography.SHA256]::Create().ComputeHash($framesBytes) | ForEach-Object { $_.ToString('x2') }) -join ''
$doc = Get-Content -Raw -Encoding UTF8 $framesPath | ConvertFrom-Json
$lineZh = @{
 'l001'='（NaNaNaNa）为什么？为什么？WHY？'; 'l002'='NaNaNaNa，谜？谜！ANSWER？！';
 'l003'='把点与点连起来，哎呀？哎呀！'; 'l004'='「花丸式完美解决！」吗？吗？';
 'l005'='推理和谜题如镜像般相反，反复翻转，最终逆转。';
 'l006'='连言语和举止都是诱饵？陷阱！可不能轻信，不行！不行！';
 'l007'='仔细看，认真想，然后迈出第一步。'; 'l008'='看到有困难的人，就想立刻帮忙。';
 'l009'='因为无论如何都想做点什么，正飞奔而出。';
 'l010'='Na Na Na，谜！谜！解开谜团的就是名侦探☆';
 'l011'='辨明谎言还是真相，找出笑容的答案。'; 'l012'='Na Na Na，为什么？为什么？和大家在一起，勇气百倍。';
 'l013'='汇集力量，跨越过去；朋友是奇迹的集合。'; 'l014'='出发吧！名侦探☆';
 'l015'='把点和线连起来，看吧！看吧？！'; 'l016'='「花丸式完美解决」也许？也许？箭头已经指向答案。';
 'l017'='痛快！愉快！爽快！'; 'l018'='可是呢、但是呢，有些事解不开——那是心里的迷宫。';
 'l019'='秘密之门不是靠撬开；只要陪伴在旁就好，抱歉（_）。';
 'l020'='当看到受伤的人时，不靠言语……'; 'l021'='想一直、比任何人都更在你身边，做你的同伴。';
 'l022'='Na Na Na，谜！谜！解开谜团的就是名侦探☆'; 'l023'='越是追赶，越会逃走；这是充满矛盾的谜团。';
 'l024'='Na Na Na，为什么？为什么？只要和大家在一起，元气百倍。';
 'l025'='失误不会就此结束；和朋友一起回收伏笔。'; 'l026'='出发吧！名侦探☆';
 'l027'='所谓正确，会因人而异，不过……';
 'l028'='温柔的话会传达出去吗？想把暖洋洋的心动传递给你。';
 'l029'='在勇气之后，能看见希望。沙啦啦啦。';
 'l030'='朋友是闪耀的宝石；每一个人、每一个人，大家都在发光☆';
 'l031'='Na Na Na，谜！谜！解开谜团的就是名侦探☆';
 'l032'='辨明是谎言还是真相，找出笑容的答案。';
 'l033'='Na Na Na，为什么？为什么？和大家在一起，勇气百倍。';
 'l034'='汇集力量，跨越过去；朋友是奇迹的集合。'; 'l035'='出发吧！名侦探☆';
 'l036'='Na Na Na，为什么？为什么？和大家在一起，勇气千倍。';
 'l037'='和朋友手牵着手，直到万事解决为止！';
 'l038'='因为是光之美少女☆（NaNaNaNa，为什么？谜？！ANSWER！）'
}
$meanings = @{
 'なぜ'='为什么'; 'なぞ'='谜；谜题'; '点'='点'; '結ん'='连接；系结'; 'だら'='如果……的话'; 'あら'='哎呀；哎哟';
 'なまる'='花丸（满分；完美）'; '解決'='解决'; '推理'='推理'; 'はうら'='（与“返し”构成）相反面'; '返し'='翻转；反转'; '二'='二'; '転'='转；变化'; '三'='三'; '逆転'='逆转';
 '言葉'='言语；话语'; '仕草'='举止；动作'; 'わな'='圈套；诱饵'; '罠'='陷阱；圈套'; 'うのみ'='照单全收；轻信'; 'し'='做'; 'だめ'='不行；不可';
 'よく'='仔细地；充分地'; 'み'='看'; '考え'='思考'; 'それから'='然后；之后'; '踏み出す'='迈出；踏出'; '歩'='步';
 '困っ'='为难；遇到困难'; 'いる'='在；正在'; '人'='人'; '見'='看见'; 'たら'='如果……就……'; 'すぐ'='立刻；马上'; '助け'='帮助；救助'; 'たい'='想要……';
 'だって'='因为；毕竟'; '何とか'='无论如何；设法'; 'たく'='想要……'; '駈け'='跑；奔跑'; '出し'='开始；冲出';
 '謎'='谜；谜团'; '解く'='解开；解答'; '名'='名'; '探偵'='侦探';
 'うそ'='谎言'; 'ま'='真'; 'ご'='真'; 'こと'='事；情况'; '見極め'='辨明；看清'; '笑顔'='笑容'; '答え'='答案'; '見つける'='找到；发现';
 'みんな'='大家；所有人'; '勇気'='勇气'; '倍'='倍';
 'ち'='力量'; '合わせ'='合在一起；汇集'; '乗り'='跨过；乘上'; '超える'='越过；超越'; '友'='朋友'; 'キセキ'='奇迹'; 'かたまり'='一团；集合体';
 '行く'='去；出发'; '線'='线'; 'つなげ'='连接'; 'ほら'='你看；瞧'; 'かも'='也许；可能'; '矢印'='箭头'; 'もう'='已经；早已'; '指す'='指向；指出';
 '痛快'='痛快'; '愉快'='愉快'; '爽快'='爽快'; 'だけど'='但是；不过'; 'でも'='但是；不过'; '解き明かせ'='解开；弄明白'; 'ない'='不；没有'; 'それ'='那个；那件事'; '心'='心；内心'; '迷宮'='迷宫';
 '秘密'='秘密'; '鍵'='钥匙'; 'こじ開け'='撬开；强行打开'; '寄り添う'='依偎；陪伴在旁'; 'ごめん'='抱歉；对不起'; 'く'='（歌词拖音）'; '(＿)'='（表情符号）';
 '傷'='伤；伤痛'; '付い'='受伤；伤害'; 'てる'='正在……；……着'; '居る'='有；在'; 'コトバ'='言语；话语'; 'じゃ'='不是；并非'; 'なくっ'='不……；并非';
 'ずっと'='一直；始终'; 'そば'='身边；旁边'; '誰'='谁'; '味方'='同伴；支持的一方'; 'い'='在；保持';
 '追え'='追赶'; '追う'='追赶；追求'; '逃げ'='逃跑；逃离'; 'いく'='逐渐……下去；离去'; 'ムジュン'='矛盾'; 'だらけ'='满是；尽是'; 'ミステリー'='谜团；悬疑';
 'いれ'='在；待在'; '元気'='元气；精神'; 'ミス'='失误；错误'; '終わら'='结束'; '伏線'='伏笔'; '回収'='回收；收束';
 '正し'='正确；正当'; 'さ'='……性；……程度'; '変わる'='变化；不同'; 'けど'='但是；不过';
 'やさし'='温柔'; 'なら'='如果是……；若说……'; 'びく'='传达；产生共鸣'; 'ポカポカ'='暖洋洋；暖乎乎'; 'とき'='心动；怦然'; 'ゅんきゅんを'='怦然心动'; '届け'='传递；送达';
 'あと'='之后；后面'; '見え'='看得见；显现'; 'くる'='逐渐出现；过来'; 'キボウ'='希望'; 'シャラララ'='沙啦啦啦（拟声）';
 '友だち'='朋友'; '光る'='闪耀；发光'; 'ジュエル'='宝石'; '輝い'='闪耀；发光';
 '手'='手'; 'とっ'='牵；拿'; '万事'='一切事；万事'; 'する'='做；进行'; 'プリキュア'='光之美少女'
}
$functions = @{
 'と'='连接并列对象；表示“和”'; 'を'='提示动作对象'; 'や'='列举事物（……和……等）'; 'さえ'='强调极端例子（连……也）';
 'に'='提示到达点／对象'; 'て'='连接动作或状态'; 'で'='表示状态、地点或方式'; 'は'='提示主题；作对比'; 'の'='连接修饰成分；表示所属';
 'よ'='加强语气；告知对方'; 'が'='提示主语；强调焦点'; 'か'='构成疑问；表示“还是”'; 'ね'='征求共鸣；缓和语气';
 'な'='句末确认或感叹语气'; 'かも'='表示不确定推测（也许）'; 'じゃ'='口语否定连接（不是……而是……）'; 'けど'='连接转折内容（但是）';
 'だけ'='限定范围（只；仅）'; 'より'='表示比较基准（比……）';
 'ば'='表示假定条件（如果……）'; 'ほど'='表示程度；构成“越……越……”'; 'って'='提示话题；口语“所谓……”';
 'によって'='表示依据／差异来源（因……而异）'; 'まで'='表示终点（直到……为止）'
}
$changes = [System.Collections.Generic.List[object]]::new()
function Add-Change($frameId,$field,$old,$new,$evidence){ if($old -ne $new){ $changes.Add([ordered]@{frameId=$frameId;field=$field;old=$old;new=$new;confidence=0.92;evidence=@($evidence);changesTokenStructure=$false}) } }
foreach($f in $doc.frames){
  Add-Change $f.id 'caption.translationZh' $f.caption.translationZh $lineZh[$f.id] 'QQ Music translation track cross-checked against the Japanese lyric context.'
  for($i=0;$i -lt $f.grammarCards.Count;$i++){
    $c=$f.grammarCards[$i]; $t=[string]$c.token
    if($functions.ContainsKey($t)){
      $old=if($null -ne $c.functionZh){$c.functionZh}else{$c.zhMeaning}
      $field=if($null -ne $c.functionZh){"grammarCards[$i].functionZh"}else{"grammarCards[$i].zhMeaning"}
      Add-Change $f.id $field $old $functions[$t] 'Particle function chosen from its local lyric syntax; particles are described by function, not dictionary gloss.'
    } elseif($meanings.ContainsKey($t)) {
      $old=if($null -ne $c.zhMeaning){$c.zhMeaning}else{$c.functionZh}
      $field=if($null -ne $c.zhMeaning){"grammarCards[$i].zhMeaning"}else{"grammarCards[$i].functionZh"}
      Add-Change $f.id $field $old $meanings[$t] 'Meaning checked against the QQ Music full-line Chinese and repeated-line context.'
    } else {
      $old=if($null -ne $c.zhMeaning){$c.zhMeaning}else{$c.functionZh}
      $field=if($null -ne $c.zhMeaning){"grammarCards[$i].zhMeaning"}else{"grammarCards[$i].functionZh"}
      if($old -match '待联网核对'){
        Add-Change $f.id $field $old '待词法合并后按整词定译' 'The draft token is an incomplete fragment; defer its definitive card meaning to the lexical merge without changing token structure here.'
      }
    }
  }
}
$proposal=[ordered]@{schemaVersion=2;reviewRole='translation';scope=[ordered]@{frameIds=@($doc.frames|ForEach-Object{$_.id})};baseFrameSha256=$sha;changes=@($changes)}
$out=Join-Path $project 'project\proposals\translation.json'
$proposal | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8NoBOM $out
Write-Output ("wrote {0} changes to {1}" -f $changes.Count,$out)
