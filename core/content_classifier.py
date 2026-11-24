# -*- coding: utf-8 -*-
"""
CLASSIFICADOR INTELIGENTE DE CONTEÚDO, BANCO DE HASHTAGS ROTATIVAS E GERADOR MULTIPLATAFORMA
Classifica automaticamente o nicho do vídeo (Música/Pagode/Sertanejo, Podcast/Entrevista, Ciência/Astronomia, Geopolítica/Militar, Games ou Geral).
Alimenta um acervo dinâmico e não-repetitivo de títulos, descrições e hashtags filtradas por gênero e número de corte,
garantindo máxima entrega e retenção no YouTube Shorts, TikTok e Kwai sem risco de detecção de spam.
"""

import re
import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Tuple

# ====================================================================
# 🏷️ FUNÇÃO DE LIMPEZA DE HASHTAGS
# ====================================================================

def limpar_tag(texto: str) -> str:
    """Normaliza acentos e remove espaços e caracteres especiais para criar hashtags 100% válidas."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    limpa = re.sub(r'[^a-zA-Z0-9]', '', sem_acento)
    return limpa

# ====================================================================
# 🏷️ POOL DE HASHTAGS FILTRADAS E CATEGORIZADAS POR NICHO
# ====================================================================

HASHTAGS_BANCO = {
    "MUSICA_PAGODE": {
        "core": ["pagode", "samba", "pagodeando"],
        "rotativas": [
            "pagode90", "rodadesamba", "churrascoepagode", "sambaepagode", "pagodinho",
            "pagodedequalidade", "pagodeaovivo", "cavaco", "pagodeiro", "sambista",
            "musicaaovivo", "churrasco", "sextou", "pagodera", "pagodinhodeleve",
            "sambanope", "cervejagelada", "alegriatotal", "pagoderaiz", "batucada"
        ]
    },
    "MUSICA_SERTANEJO": {
        "core": ["sertanejo", "arrocha", "sofrência"],
        "rotativas": [
            "modao", "modadeviola", "sertanejouniversitario", "sertanejobr", "sofrencia",
            "arrochando", "sertanejoaovivo", "musicasertaneja", "statusmusica", "trechosdemusicas",
            "letrasdemusica", "arrochadeira", "modaoantigo", "coracaomachucado", "sofrendoporamor",
            "cantoriasertaneja", "violaoevoz", "modaboa", "sertanejando", "amordesertanejo"
        ]
    },
    "MUSICA_GERAL": {
        "core": ["musica", "showaovivo", "clipeoficial"],
        "rotativas": [
            "musicabrasileira", "mpb", "musicaaovivo", "shows", "melhoresmusicas",
            "aovivo", "hitdomomento", "letrasdemusica", "trechodemusica", "musicaévida",
            "musicaparastatus", "sucessomusical", "cantarjunto", "somdequalidade", "clipemusical"
        ]
    },
    "CIENCIA_ASTRONOMIA": {
        "core": ["astronomia", "ciencia", "universo"],
        "rotativas": [
            "spacetoday", "sergiosacani", "fisica", "astrofisica", "espaco",
            "jameswebb", "nasa", "buraconegro", "planetas", "curiosidades",
            "cienciatododia", "fatosdesconhecidos", "misteriosdouniverso", "exploracaoespacial", "sistemasolar",
            "galaxia", "estrelas", "ciencianoar", "aprendersempre", "fatoscuriosos"
        ]
    },
    "HISTORIA_GEOPOLITICA": {
        "core": ["historia", "geopolitica", "militar"],
        "rotativas": [
            "guerradaucrania", "fabiorocco", "podcast3irmaos", "exercito", "forcasarmadas",
            "noticias", "relatodecombate", "frontdeguerra", "estrategiamilitar", "conflitos",
            "historiadevida", "depoimentoreal", "documentario", "bastidoresdaguerra", "relatoreal",
            "historiadomundo", "geopoliticamundial", "defesa", "guerraemdebate", "relatochocante"
        ]
    },
    "PODCAST_GERAL": {
        "core": ["podcast", "entrevista", "cortespodcast"],
        "rotativas": [
            "podcastsbrasil", "conversaboa", "batepapo", "videocast", "cortesdepodcast",
            "opiniao", "reflexao", "visaodevida", "conhecimento", "aprendizado",
            "historiasincriveis", "debates", "convidadoespecial", "pensamentododia", "visão",
            "mentoria", "conversaafiada", "conselhos", "pensenisso", "cortesvirais"
        ]
    },
    "GAMES": {
        "core": ["games", "gameplay", "jogos"],
        "rotativas": [
            "streamer", "streamersbrasil", "clipadas", "jogadasinsanas", "twitchbrasil",
            "kickbrasil", "pcgamer", "jogosonline", "highlights", "melhoresmomentos",
            "fpsgames", "momentosgamer", "gamerbrasil", "clipesdetwitch", "jogadadodia",
            "proplayer", "gameplaybrasil", "comedia", "humorgamer", "fugasinsanas"
        ]
    },
    "CINEMA_FILMES": {
        "core": ["cinema", "filmes", "marvel"],
        "rotativas": [
            "vingadores", "vingadoresultimato", "avengersendgame", "homemdeferro",
            "capitaoamerica", "thor", "thanos", "cenasdefilmes", "filmeseseries",
            "trechosdefilmes", "melhorescenas", "cinematografia", "marvelbrasil", "mcu",
            "nerd", "geek", "culturapop", "filmesmarcantes", "cenasmarcantes",
            "filme", "marvelfilms", "avengersassemble", "marveltok", "cenasclassicas"
        ]
    },
    "GERAL": {
        "core": ["viral", "curiosidades", "emalta"],
        "rotativas": [
            "videoviral", "fatoscuriosos", "voceprecisaveer", "entretenimento", "incrivel",
            "surpreendente", "tendencias", "destaques", "compartilhe", "momentosunicos",
            "fatosinacreditaveis", "naoacredito", "reflexaododia", "parastatus", "topvideos"
        ]
    }
}

TAGS_PLATAFORMA = {
    "shorts": ["Shorts", "ShortsBrasil", "ShortsViral", "YouTubeShorts"],
    "tiktok": ["foryou", "fyp", "viral", "foryoupage", "trend", "fy"],
    "kwai": ["kwai", "statuswhatsapp", "videoparawhatsapp", "kwaibrasil", "statusdodia"]
}

# ====================================================================
# 📚 BANCO DE MODELOS ROTATIVOS DE TÍTULOS E DESCRIÇÕES POR GÊNERO
# ====================================================================

MODELOS_TITULOS_SHORTS = {
    "MUSICA_PAGODE": [
        "{artista} - Pagodinho ao vivo! 🥁 #Shorts",
        "Aquele samba que arrepia! 🍻 | {artista} #Shorts",
        "Quem nunca cantou essa no churrasco? 🎶 #Shorts",
        "{artista} mandou bem demais ao vivo! 🔥 #Shorts",
        "Pura energia de pagode de raiz! 🥁 #Shorts",
        "Esse refrão não sai da cabeça! 🎵 #Shorts",
        "{artista} cantando com a alma! 🍻 #Shorts",
        "Roda de samba emocionante! 🥁 #Shorts",
        "O melhor do pagode brasileiro! 🎶 #Shorts",
        "Clima perfeito de domingo e pagode! ☀️ #Shorts"
    ],
    "MUSICA_SERTANEJO": [
        "{artista} - Que emoção ao vivo! 💔 #Shorts",
        "Essa música machuca o peito! 😭 | {artista} #Shorts",
        "Quem nunca chorou ouvindo essa? 💔 #Shorts",
        "{artista} cantou com o coração! 🎶 #Shorts",
        "O refrão que todo mundo canta junto! 🥺 #Shorts",
        "Hino da sofrência ao vivo! 💔 | {artista} #Shorts",
        "Letra que fala direto na alma! 🎵 #Shorts",
        "Essa bateu forte na ferida! 😭 #Shorts",
        "{artista} ao vivo é outro nível! 🔥 #Shorts",
        "Momento mais emocionante do show! 💔 #Shorts"
    ],
    "MUSICA_GERAL": [
        "{artista} - Que voz impressionante! 🎶 #Shorts",
        "Esse momento do show foi épico! 🔥 #Shorts",
        "A plateia inteira cantou junto! 🎤 #Shorts",
        "{artista} dando show no palco! ✨ #Shorts",
        "Uma das melhores interpretações! 🎶 #Shorts",
        "Impossível não se arrepiar ouvindo! 🎵 #Shorts",
        "Momento inesquecível ao vivo! 🌟 #Shorts",
        "{artista} surpreendeu a todos! 🔥 #Shorts"
    ],
    "CIENCIA_ASTRONOMIA": [
        "Sérgio Sacani explica o universo! 🌌 #Shorts",
        "O mistério do espaço que chocou a ciência! 🪐 #Shorts",
        "Você sabia desse segredo cósmico? 🤯 #Shorts",
        "Sacani revela o que ninguém te contou! 🔭 #Shorts",
        "A ciência explica esse fenômeno raro! 🌌 #Shorts",
        "Isso muda sua visão sobre o universo! 🧠 #Shorts",
        "Como isso é possível no espaço?! 🛰️ #Shorts",
        "Sacani deixando todo mundo de queixo caído! 🤯 #Shorts",
        "A verdade fascinante sobre o cosmos! 🌌 #Shorts",
        "Mistério da física finalmente explicado! 🔬 #Shorts"
    ],
    "HISTORIA_GEOPOLITICA": [
        "Relato real do front na Ucrânia! 🪖 #Shorts",
        "Fábio Rocco conta a realidade do combate! ⚠️ #Shorts",
        "A dura verdade que a mídia não mostra! 🪖 #Shorts",
        "Depoimento chocante de veterano do front! ⚠️ #Shorts",
        "O que realmente acontece no campo de batalha! 🪖 #Shorts",
        "Relato contundente que calou o estúdio! 🤫 #Shorts",
        "Sobrevivendo ao front: história real! 🪖 #Shorts",
        "A realidade crua da guerra moderna! ⚠️ #Shorts",
        "Depoimento histórico e emocionante! 🪖 #Shorts",
        "Fábio Rocco abre o jogo sobre o front! ⚠️ #Shorts"
    ],
    "PODCAST_GERAL": [
        "Essa revelação impressionou a todos! 😱 #Shorts",
        "Você concorda com essa opinião sincera? 🗣️ #Shorts",
        "Ele falou a verdade que ninguém admite! 🤯 #Shorts",
        "A história que pegou todo mundo de surpresa! 🎙️ #Shorts",
        "Visão impressionante sobre a vida real! 🧠 #Shorts",
        "O momento mais polêmico da conversa! 💥 #Shorts",
        "Lição valiosa que vale para todo mundo! ✨ #Shorts",
        "Debate pegou fogo no estúdio! 🎙️ #Shorts"
    ],
    "GAMES": [
        "A jogada mais insana da semana! 🔥 #Shorts",
        "Como ele conseguiu escapar dessa?! 😱 #Shorts",
        "A reação dele foi a mais engraçada! 😂 #Shorts",
        "O final desse clipe foi surreal! 🎮 #Shorts",
        "Momento de puro reflexo ao vivo! ⚡ #Shorts",
        "Quando tudo dá errado na gameplay! 🤣 #Shorts",
        "A mira mais absurda da live! 🎯 #Shorts",
        "Nem ele acreditou no que fez! 😱 #Shorts"
    ],
    "CINEMA_FILMES": [
        "A cena mais épica da história do cinema! 🎬 #Shorts",
        "O momento que arrepiou o mundo inteiro! 🔥 #Shorts",
        "Essa cena ficou marcada para sempre! 😱 #Shorts",
        "Impossível não se emocionar com essa cena! 🥺 #Shorts",
        "O maior clímax de todos os tempos! ⚡ #Shorts",
        "Você lembra da sensação de ver isso no cinema? 🍿 #Shorts",
        "A cena que fez a sala de cinema inteira explodir! 💥 #Shorts",
        "O sacrifício mais emocionante de todos! 💔 #Shorts",
        "Arrepia do começo ao fim! 🎬 #Shorts",
        "Simplesmente cinema em sua forma mais pura! ✨ #Shorts"
    ],
    "GERAL": [
        "Você não vai acreditar no que aconteceu! 😱 #Shorts",
        "Esse momento surpreendeu todo mundo! ✨ #Shorts",
        "Alguém consegue explicar o que foi isso?! 🤯 #Shorts",
        "O desfecho desse vídeo é inacreditável! 🚀 #Shorts",
        "Fato impressionante que você precisa ver! 💡 #Shorts",
        "Momento raro capturado em vídeo! 👁️ #Shorts"
    ]
}

MODELOS_COPIES_TIKTOK = {
    "MUSICA_PAGODE": [
        "Aquele pagodinho que não pode faltar no churrasco de domingo! 🍻🥁 Marca quem vai tomar uma gelada ouvindo essa com você! 👇🎶",
        "Quem tem samba no pé sente essa batida no peito! 🥁✨ Marca a pessoa que sabe cantar esse refrão todinho! 👇",
        "POV: Você colocou aquela playlist de pagode antigo e o dia virou festa na hora! 🍻☀️ Quem aí ama esse som? 👇",
        "Se você não sabe esse refrão, tá vivendo no Brasil errado! 🇧🇷🎶 Deixa nos comentários qual a sua música favorita dele! 👇",
        "Clima perfeito de roda de samba com os amigos! 🥁❤️ Marca quem você levaria pra esse show agora mesmo! 👇"
    ],
    "MUSICA_SERTANEJO": [
        "Quem aí já viveu uma história parecida? 💔🥺 Marca a pessoa que veio na sua cabeça ouvindo o {artista}! 👇🎶",
        "POV: A música começou a tocar e o coração apertou na hora... 💔😭 Quem se identifica, comenta aí! 👇",
        "Essa música foi feita pra quem já amou demais e se machucou... 🥺💔 Marca quem precisa ouvir essa mensagem hoje! 👇",
        "O {artista} cantou com a alma nessa hora! 🎶💔 Deixa um emoji que resume o que você sentiu ouvindo esse trecho! 👇",
        "Se essa letra não te fez lembrar de alguém especial, você tem um coração de gelo! 🧊💔 Concorda? 👇"
    ],
    "MUSICA_GERAL": [
        "A performance ao vivo de {artista} foi simplesmente espetacular! 🔥🎶 O que você achou dessa apresentação? 👇",
        "Impossível não sentir a energia dessa música! ✨🎤 Marca um amigo que também é fã de {artista}! 👇",
        "Quando o cantor entrega tudo no palco, o resultado é de arrepiar! 🌟🎵 Qual nota você dá pra esse corte? 👇"
    ],
    "CIENCIA_ASTRONOMIA": [
        "O Sacani explicou esse mistério cósmico com uma clareza surreal! 🤯🔭 O que você acha dessa teoria? Comenta aí! 👇🌌",
        "Você já sabia dessa curiosidade impressionante ou descobriu agora com o Sacani? 🤯 Deixa sua opinião sincera! 👇",
        "POV: O Sacani começa a explicar o tamanho do universo e você percebe o quanto somos pequenos! 🌌🧠 O que pensa sobre isso? 👇",
        "A mente chega a explodir ouvindo isso! 🤯🔬 Você acredita que estamos sozinhos no universo? Deixa nos comentários! 👇",
        "Conhecimento de alto nível com Sacani! 🌌✨ Marca um amigo que ama astronomia e ciência! 👇🔭"
    ],
    "HISTORIA_GEOPOLITICA": [
        "O relato impressionante de quem esteve no front de batalha! 🪖⚠️ O que você achou dessa história contada pelo Fábio Rocco? Deixa nos comentários! 👇",
        "A dura e chocante realidade da guerra que a televisão não mostra. 🪖 Qual parte desse relato mais te impressionou? 👇",
        "Um depoimento contundente de quem viu a história acontecer de perto. ⚠️ Deixe sua opinião sincera e respeitosa nos comentários! 👇",
        "Relatos como esse nos mostram o verdadeiro valor da paz. 🪖🕊️ O que você sentiu ouvindo esse trecho? 👇",
        "Fábio Rocco abriu o jogo sem rodeios sobre o front. 🪖⚠️ Já imaginou passar por uma situação dessas? Comenta aí! 👇"
    ],
    "PODCAST_GERAL": [
        "Você concorda com o que ele disse aqui? 🤯 Deixa sua opinião sincera nos comentários! 👇🗣️",
        "POV: Quando o convidado solta aquela verdade que ninguém tinha coragem de dizer... 🤯 Qual sua visão sobre isso? 👇",
        "Essa reflexão me fez pensar o dia todo. 🧠✨ Você faria o mesmo no lugar dele? Deixa nos comentários! 👇",
        "Um ponto de vista maduro sobre um assunto delicado. 🎙️ Concorda ou discorda do que foi dito? 👇"
    ],
    "GAMES": [
        "Quem aí conseguiria fazer essa jogada? 🔥🎮 Marca o amigo que ia morrer na hora nessa situação! 👇🤣",
        "A reação dele no final foi a melhor da live inteira! 🤣🔥 Qual nota você daria pra essa jogada de 0 a 10? 👇",
        "Quando a sorte se junta com a habilidade pura! 🎮⚡ Você teria coragem de arriscar isso? 👇",
        "Não existe streamer mais engraçado que esse! 😂🎮 Marca quem precisa rir desse clipe hoje! 👇"
    ],
    "CINEMA_FILMES": [
        "Essa cena de {artista} no cinema fez a sala inteira explodir de emoção! 🎬🍿 Qual foi sua reação na primeira vez que viu isso? Comenta aí! 👇",
        "Aquele momento que você assiste 100 vezes e ainda se arrepia do começo ao fim! ⚡🎬 Deixa nos comentários qual seu herói favorito! 👇",
        "POV: Você estava no cinema no lançamento desse filme e presenciou a história acontecer! 🔥🥺 Quem lembra dessa sensação? Comenta aí! 👇",
        "Uma das cenas mais épicas e inesquecíveis já feitas na história da Marvel! 🎬💥 Concorda ou tem outra melhor? Deixa nos comentários! 👇"
    ],
    "GERAL": [
        "Olha o que aconteceu aqui! 😱 Deixa nos comentários o que você achou dessa cena! 👇🔥",
        "Você esperava por esse final ou foi pego de surpresa? 🤯 Comenta aí embaixo! 👇",
        "Momento inacreditável gravado na hora certa! ✨ Deixe sua opinião nos comentários! 👇"
    ]
}

MODELOS_COPIES_KWAI = {
    "MUSICA_PAGODE": [
        "Pura energia boa e samba no pé! 🥁✨ Aquele pagode que alegra o dia de qualquer um. Compartilhe no seu status do WhatsApp para animar os amigos! 📲🍺",
        "Música boa de verdade alegra a alma! 🥁🎶 Salve esse vídeo e compartilhe no grupo da família e do churrasco! 📲✨",
        "Aquele pagodinho que faz a gente esquecer os problemas e só sorrir! 🍻🥁 Envie pra quem ama um bom samba no WhatsApp! 📲",
        "Coisa linda de se ouvir! 🎶 A tradição do pagode brasileiro ao vivo. Compartilhe no seu status! 📲✨"
    ],
    "MUSICA_SERTANEJO": [
        "Essa música é pra quem tá com o coração machucado... 💔 {artista} cantou com a alma! Compartilhe no seu status do WhatsApp! 📲✨",
        "Letra linda que toca lá no fundo da alma... 🥺💔 Salve esse vídeo para postar no seu status do WhatsApp hoje! 📲",
        "Para todos os corações apaixonados que já sofreram por amor... 💔😭 Envie para alguém especial no WhatsApp! 📲✨",
        "Quem nunca viveu uma história assim? 💔 {artista} transmitiu pura emoção! Compartilhe no seu status! 📲",
        "Uma oração em forma de canção para quem precisa de paz no coração. 🙏💔 Compartilhe com quem você ama no WhatsApp! 📲"
    ],
    "MUSICA_GERAL": [
        "Música é a arte que fala direto ao coração! 🎶✨ Compartilhe esse momento especial no seu status do WhatsApp! 📲",
        "Um show emocionante que vale a pena rever e compartilhar! 🎤🌟 Mande para os amigos no WhatsApp! 📲"
    ],
    "CIENCIA_ASTRONOMIA": [
        "Conhecimento que expande a mente! 🌌🧠 Entenda esse mistério fascinante com Sérgio Sacani. Compartilhe no grupo do WhatsApp! 📲✨",
        "O universo é muito mais incrível do que imaginamos! 🪐🔭 Salve esse vídeo educativo e mande para quem ama ciência! 📲",
        "Aprender coisas novas todos os dias faz bem pra mente! 💡🌌 Sérgio Sacani explicando com maestria. Compartilhe! 📲",
        "Uma verdadeira aula rápida sobre os mistérios do espaço! 🛰️🧠 Mande no WhatsApp para os amigos e filhos aprenderem! 📲"
    ],
    "HISTORIA_GEOPOLITICA": [
        "A dura e chocante realidade do front de combate. 🪖 Um depoimento histórico que todos deveriam ouvir. Compartilhe no WhatsApp! 📲",
        "Histórias reais que mostram a coragem e os desafios extremos da guerra. 🪖 Salve e compartilhe com os amigos! 📲",
        "Um testemunho emocionante sobre sobrevivência e realidade militar. ⚠️ Compartilhe essa reflexão profunda no WhatsApp! 📲",
        "Relato histórico que precisa ser lembrado. 🪖🕊️ Compartilhe no grupo dos amigos e família! 📲"
    ],
    "PODCAST_GERAL": [
        "Ouça com atenção o que ele acabou de revelar! 🧠 Reflexão profunda sobre a vida. Salve e compartilhe no status do WhatsApp! 📲",
        "Uma lição de vida que todos nós deveríamos praticar no dia a dia. ✨ Compartilhe com quem você quer bem! 📲",
        "Palavras sábias que valem mais do que ouro! 💡🧠 Salve esse vídeo e compartilhe no status hoje! 📲"
    ],
    "GAMES": [
        "Olha a habilidade do cara jogando! 🎮🔥 Mandou muito bem! Salve esse vídeo e compartilhe no grupo dos amigos gamers! 📲",
        "A gargalhada do dia garantida com esse clipe! 🤣🎮 Envie pros parceiros de jogo no WhatsApp! 📲"
    ],
    "CINEMA_FILMES": [
        "A cena mais emocionante do cinema! 🎬🍿 Salve esse vídeo e mande no grupo dos amigos e da família que amam filmes! 📲✨",
        "Uma cena épica que marcou a história dos cinemas! 🎬⚡ Compartilhe no seu status do WhatsApp hoje! 📲"
    ],
    "GERAL": [
        "Momento impressionante! ✨ Salve esse vídeo e compartilhe com os amigos no WhatsApp! 📲",
        "Aquele vídeo que você precisa compartilhar no status pra todo mundo ver! 🌟📲 Compartilhe agora!",
        "Uma mensagem bonita e surpreendente para abençoar o seu dia! ☀️✨ Mande no WhatsApp! 📲"
    ]
}

MODELOS_DESCRICAO_SHORTS = {
    "MUSICA_PAGODE": [
        "Trecho ao vivo contagiante de {artista} no projeto '{tema}'.\nInscreva-se no canal para acompanhar os melhores cortes de samba e pagode diários!\nDeixe seu like e mande no grupo do churrasco.\n\nArtista: {artista}\nObra: {tema}",
        "Aquele pagode diferenciado com {artista}! Música de qualidade para curtir com a galera.\nInscreva-se para novos cortes diários das melhores rodas de samba do Brasil!\n\nArtista: {artista}\nProjeto: {tema}",
        "Show completo de {artista} trazendo os maiores sucessos do pagode!\nCurtiu esse trecho? Deixe o like, comente e inscreva-se para não perder nenhum lançamento!\n\nArtista: {artista}\nÁlbum: {tema}"
    ],
    "MUSICA_SERTANEJO": [
        "Apresentação emocionante de {artista} no projeto '{tema}'.\nInscreva-se no canal para acompanhar os melhores lançamentos e cortes da música brasileira!\nDeixe seu like e compartilhe com quem ama essa canção.\n\nArtista: {artista}\nObra: {tema}",
        "Trecho marcante que toca no fundo do coração com {artista}.\nSe inscreva para receber cortes diários de modão, sofrência e grandes clássicos sertanejos!\n\nArtista: {artista}\nProjeto: {tema}",
        "Momento inesquecível ao vivo de {artista}! A plateia cantou do início ao fim.\nInscreva-se, ative as notificações e compartilhe com os amigos!\n\nArtista: {artista}\nObra: {tema}"
    ],
    "CIENCIA_ASTRONOMIA": [
        "Sérgio Sacani explica detalhes impressionantes sobre {tema}.\nGosta de ciência, astronomia e exploração espacial? Inscreva-se no canal para acompanhar cortes diários!\n\nEspecialista: Sérgio Sacani (Space Today)\nAssunto: {tema}",
        "Um dos melhores cortes explicativos de Sérgio Sacani sobre os mistérios do cosmos e {tema}.\nInscreva-se para aprender ciência e astronomia de forma simples todos os dias!\n\nCanal: Space Today / Sacani\nTema: {tema}"
    ],
    "HISTORIA_GEOPOLITICA": [
        "Depoimento contundente de Fábio Rocco sobre a dura realidade do front de batalha em {tema}.\nInscreva-se no canal para acompanhar entrevistas e relatos históricos exclusivos!\n\nEntrevistado: Fábio Rocco\nPrograma: Podcast 3 Irmãos",
        "Relato histórico e militar exclusivo sobre {tema}.\nInscreva-se no canal para não perder novos episódios, entrevistas e análises aprofundadas!\n\nTema: {tema}\nConvidado: Fábio Rocco"
    ],
    "PODCAST_GERAL": [
        "Corte imperdível com {artista} em {tema}.\nInscreva-se no canal para acompanhar os melhores cortes de entrevistas e bate-papos do Brasil!\n\nParticipação: {artista}\nTema: {tema}",
        "Debate de alto nível e reflexão profunda com {artista}.\nDeixe seu like e inscreva-se para acompanhar os episódios completos!\n\nConvidado: {artista}\nEpisódio: {tema}"
    ],
    "GAMES": [
        "Melhores momentos e jogadas insanas de {artista} jogando {tema}.\nInscreva-se no canal para acompanhar clipes diários das maiores lives e streams!\n\nStreamer: {artista}\nJogo: {tema}",
        "As melhores reações e jogadas hilárias com {artista}!\nCurtiu? Inscreva-se no canal para não perder as próximas clipadas!\n\nCanal: {artista}\nGame: {tema}"
    ],
    "CINEMA_FILMES": [
        "Reviva essa cena inesquecível de {tema} que marcou toda uma geração nos cinemas. Qual foi sua reação ao ver isso pela primeira vez?\n\nDeixe seu like e se inscreva no canal para mais cenas épicas do cinema!\n\nFilme: {artista}\nCena: {tema}",
        "Um dos momentos mais impactantes e emocionantes do cinema mundial ({tema}). O que você sentiu quando essa cena aconteceu?\n\nComente sua opinião, deixe seu like e compartilhe com os amigos!\n\nObra: {artista}\nDestaque: {tema}",
        "Aquele momento de arrepiar em {tema} que ninguém jamais vai esquecer. Toda vez que assisto é de tirar o fôlego!\n\nInscreva-se no canal para não perder os melhores cortes de filmes!\n\nFilme: {artista}\nMomento: {tema}"
    ],
    "GERAL": [
        "Destaque especial de {tema}.\nInscreva-se no canal para acompanhar os melhores vídeos virais e novidades diariamente!\n\nTema: {tema}",
        "Momento imperdível capturado em {tema}.\nDeixe o like, comente e inscreva-se para mais conteúdos diários!\n\nAssunto: {tema}"
    ]
}

# ====================================================================
# ⚙️ FUNÇÕES DE CLASSIFICAÇÃO E MONTAGEM INTELIGENTE
# ====================================================================

def descrever_enquadramento_crop(layout_tipo: str) -> Dict[str, str]:
    """Retorna a explicação técnica e prática do crop visual aplicado ao vídeo."""
    mapa = {
        "FULL_BLEED_ZOOM": {
            "nome": "Tela Cheia 9:16 com Micro-Zoom de Clímax (Full Bleed)",
            "proporcao": "1080x1920 (9:16 Vertical Nativo)",
            "area_crop": "Corte vertical centralizado (extração 9:16 da fonte panorâmica 16:9), eliminando 100% das barras pretas.",
            "detalhes": "Recorta as laterais do vídeo 16:9 original mantendo o foco dinâmico no centro da cena. Aplica micro-zooms sutis (punch-in de 105% a 110%) nos momentos de pico sonoro para prender os primeiros 3 segundos de atenção no celular."
        },
        "SPLIT_PRO": {
            "nome": "Split Screen Pro (Apresentador Topo + Conteúdo Base)",
            "proporcao": "1080x1920 (9:16 Vertical Dividido)",
            "area_crop": "Câmera do apresentador/convidado no terço superior (38% da altura) e tela/jogo/cena nos 62% inferiores.",
            "detalhes": "Rastreia a face do apresentador via YuNet, enquadra no topo com divisória profissional de estúdio e exibe a ação ou corte principal na parte inferior."
        },
        "DUAL_FOCUS": {
            "nome": "Dual Focus Viral (Visão Geral 16:9 + Zoom Dinâmico de Ação)",
            "proporcao": "1080x1920 (9:16 Vertical)",
            "area_crop": "Vídeo original 16:9 completo no topo e zoom de ação 9:16 na base.",
            "detalhes": "Preserva o contexto panorâmico completo no bloco superior enquanto o bloco inferior amplia os detalhes cruciais de movimento e reação."
        },
        "BLUR_BACKGROUND": {
            "nome": "Fundo Desfocado Moderno (16:9 Central + Blur Lateral Dinâmico)",
            "proporcao": "1080x1920 (9:16 Vertical)",
            "area_crop": "Sem corte do conteúdo original; vídeo 16:9 preservado na íntegra.",
            "detalhes": "Posiciona o vídeo 16:9 no centro horizontal e preenche as faixas verticais superior e inferior com o próprio vídeo espelhado em desfoque gaussiano suave (Gaussian Blur)."
        },
        "CUSTOM_SPLIT": {
            "nome": "Studio Interativo (Ajuste Manual Personalizado)",
            "proporcao": "1080x1920 (9:16 Vertical)",
            "area_crop": "Coordenadas X/Y e dimensões personalizadas via Studio Web.",
            "detalhes": "Enquadramento sob medida definido pelo usuário via Studio de Crop Interativo no navegador, permitindo redimensionar câmera e tela com precisão milimétrica."
        }
    }
    return mapa.get(layout_tipo, mapa["FULL_BLEED_ZOOM"])

def extrair_entidade_e_titulo(titulo_ou_arquivo: str) -> Tuple[str, str]:
    """Limpa o nome do arquivo para extrair o Artista/Canal e o Nome da Obra de forma inteligente."""
    try:
        limpo = Path(titulo_ou_arquivo).stem if ("." in titulo_ou_arquivo or "/" in titulo_ou_arquivo or "\\" in titulo_ou_arquivo) else str(titulo_ou_arquivo)
    except Exception:
        limpo = str(titulo_ou_arquivo)
        
    limpo = re.sub(r"^(original_|corte_\d+_|video_by_|cortes_)", "", limpo, flags=re.IGNORECASE)
    limpo = limpo.replace("[", "").replace("]", "").replace("_", " ").strip()
    
    # Remove prefixos comuns de compilações/lives
    limpo = re.sub(r"^[🔥\s\d]*horas?\s*de\s*", "", limpo, flags=re.IGNORECASE).strip()
    limpo = re.sub(r"\b(audiovisual completo|dvd completo|dvd oficial|clipe oficial|vídeo oficial|video oficial|ao vivo|vod|hd|1080p|720p)\b", "", limpo, flags=re.IGNORECASE).strip()
    limpo = re.sub(r"[🔥🎉✨⭐💥]", "", limpo).strip()
    limpo = re.sub(r"\s+", " ", limpo).strip()
    
    # Casos específicos conhecidos
    t_lower = limpo.lower()
    if "sergio sacani" in t_lower or "sacani" in t_lower:
        return "Sergio Sacani", "Astronomia e Mistérios do Espaço"
    if "menos é mais" in t_lower or "menos e mais" in t_lower:
        return "Grupo Menos é Mais", "Churrasquinho Menos é Mais"
    if "pagode 90" in t_lower or "pagode do leleco" in t_lower:
        return "Pagode do Leleco", "Pagode 90 na Praia"
    if "marília mendonça" in t_lower or "marilia mendonca" in t_lower:
        return "Marília Mendonça", "Os Sucessos da Rainha"
    if "pablo" in t_lower and "dvd 20 anos" in t_lower:
        return "Pablo", "DVD 20 Anos de Sucesso"
    if "natanzinho" in t_lower and "leonardo" in t_lower:
        return "Natanzinho Lima e Leonardo", "Um Sonhador (DVD Na Liga)"
    if "guerra da ucrânia" in t_lower or "fabio rocco" in t_lower:
        return "Fábio Rocco", "Guerra da Ucrânia: O Lado Sombrio do Front"
    if "heitor santos" in t_lower:
        return "Heitor Santos", "Sabor HS 2.0"
    if "vingadores" in t_lower or "ultimato" in t_lower or "avengers" in t_lower:
        return "Vingadores: Ultimato", "Melhores Momentos e Cenas Épicas"

    partes = [p.strip() for p in re.split(r"[-–|:]", limpo) if p.strip()]
    if len(partes) >= 2:
        artista = partes[0]
        tema = " - ".join(partes[1:])
    else:
        artista = limpo
        tema = limpo
        
    return artista.title(), tema.title()

def identificar_nicho_conteudo(titulo_ou_arquivo: str, categoria: str = "") -> str:
    """Identifica o nicho e sub-nicho com base no nome do arquivo, título e categoria."""
    texto = f"{titulo_ou_arquivo} {categoria}".lower()
    
    if any(k in texto for k in ["pagode", "samba", "menos é mais", "menos e mais", "leleco", "churrasquinho", "ferrugem", "thiaguinho", "dilsinho"]):
        return "MUSICA_PAGODE"
    if any(k in texto for k in ["heitor santos", "pablo", "marília", "marilia", "leonardo", "natanzinho", "sertanejo", "arrocha", "forró", "forro", "sofrência", "sofrencia"]):
        return "MUSICA_SERTANEJO"
    if any(k in texto for k in ["show", "audiovisual", "dvd", "clipe oficial", "álbum", "album", "cantor", "cantora", "ao vivo", "musica", "música"]):
        return "MUSICA_GERAL"
    if any(k in texto for k in ["sacani", "sergio sacani", "astronomia", "espaço", "espaco", "universo", "planeta", "física", "fisica", "james webb", "nasa"]):
        return "CIENCIA_ASTRONOMIA"
    if any(k in texto for k in ["guerra", "ucrânia", "ucrania", "front", "fábio rocco", "fabio rocco", "militar", "exército", "combate", "história", "historia"]):
        return "HISTORIA_GEOPOLITICA"
    if any(k in texto for k in ["podcast", "inteligência ltda", "inteligencia ltda", "flow", "podpah", "entrevista", "podcast 3 irmãos", "bate papo", "debate"]):
        return "PODCAST_GERAL"
    if any(k in texto for k in ["gta", "grand theft auto", "cs2", "counter-strike", "valorant", "fortnite", "roblox", "minecraft", "gameplay", "streamer", "dilera", "alanzoka", "cellbit", "xarola"]):
        return "GAMES"
    if any(k in texto for k in ["vingadores", "ultimato", "avengers", "marvel", "filme", "filmes", "cinema", "homem de ferro", "thanos", "capitão américa", "thor"]):
        return "CINEMA_FILMES"
        
    return "GERAL"

def filtrar_hashtags_dinamicas(
    nicho: str,
    artista: str,
    tema: str,
    plataforma: str,
    numero_corte: int = 1,
    max_tags: int = 7
) -> str:
    """
    Gera uma lista de hashtags exclusivas, limpas (sem acentos e sem espaços) e rotativas para o corte atual,
    evitando padrões repetitivos detectáveis por algoritmos sociais.
    """
    tags_banco = HASHTAGS_BANCO.get(nicho, HASHTAGS_BANCO["GERAL"])
    core_tags = tags_banco["core"]
    rotativas_pool = tags_banco["rotativas"]
    plat_tags = TAGS_PLATAFORMA.get(plataforma.lower(), ["viral", "foryou"])
    
    # 1. Tag de Marca / Artista / Tema (limpa de acentos)
    tag_art = limpar_tag(artista)
    tag_tem = limpar_tag(tema)
    
    tags_finais = []
    if tag_art and len(tag_art) >= 3:
        tags_finais.append(f"#{tag_art}")
    if tag_tem and len(tag_tem) >= 3 and tag_tem.lower() != tag_art.lower() and len(tag_tem) <= 20:
        tags_finais.append(f"#{tag_tem}")
        
    # 2. Tag da Plataforma
    idx_p = (numero_corte - 1) % len(plat_tags)
    tags_finais.append(f"#{plat_tags[idx_p]}")
    
    # 3. Tags Core do Nicho
    for c in core_tags[:2]:
        tags_finais.append(f"#{limpar_tag(c)}")
        
    # 4. Tags Rotativas (seleção cíclica com salto de 3 para garantir diversidade entre cortes)
    n_rot = len(rotativas_pool)
    offset = ((numero_corte - 1) * 3) % n_rot
    tags_restantes = max_tags - len(tags_finais)
    
    for i in range(max(1, tags_restantes)):
        tag_cand = rotativas_pool[(offset + i) % n_rot]
        tag_fmt = f"#{limpar_tag(tag_cand)}"
        if tag_fmt not in tags_finais:
            tags_finais.append(tag_fmt)
            
    return " ".join(tags_finais[:max_tags])

def gerar_pacote_multiplataforma(
    titulo_ou_arquivo: str,
    categoria: str,
    layout_tipo: str,
    transcricao: str = "",
    c_start: float = 0.0,
    c_dur: float = 40.0,
    numero_corte: int = 1
) -> Dict[str, Any]:
    """
    Gera o pacote completo e variado de publicação para YouTube Shorts, TikTok e Kwai
    baseado no nicho e no índice do corte, garantindo títulos e descrições não repetitivas.
    """
    nicho = identificar_nicho_conteudo(titulo_ou_arquivo, categoria)
    artista, tema = extrair_entidade_e_titulo(titulo_ou_arquivo)
    info_crop = descrever_enquadramento_crop(layout_tipo)
    
    m_ini, s_ini = int(c_start // 60), int(c_start % 60)
    c_fim = c_start + c_dur
    m_fim, s_fim = int(c_fim // 60), int(c_fim % 60)

    # 1. Geração de Título de Shorts Rotativo
    titulos_pool = MODELOS_TITULOS_SHORTS.get(nicho, MODELOS_TITULOS_SHORTS["GERAL"])
    idx_t = (numero_corte - 1) % len(titulos_pool)
    shorts_titulo = titulos_pool[idx_t].format(artista=artista, tema=tema)
    if len(shorts_titulo) > 52:
        shorts_titulo = f"{artista} - Corte #{numero_corte:02d}! 💔 #Shorts"
        if len(shorts_titulo) > 52:
            shorts_titulo = f"{artista} ao vivo! 🎶 #Shorts"

    # 2. Geração de Descrição de Shorts Rotativa
    desc_pool = MODELOS_DESCRICAO_SHORTS.get(nicho, MODELOS_DESCRICAO_SHORTS["GERAL"])
    idx_d = (numero_corte - 1) % len(desc_pool)
    desc_base = desc_pool[idx_d].format(artista=artista, tema=tema)
    
    # Tags filtradas para cada plataforma
    tags_shorts = filtrar_hashtags_dinamicas(nicho, artista, tema, "shorts", numero_corte, max_tags=7)
    tags_tiktok = filtrar_hashtags_dinamicas(nicho, artista, tema, "tiktok", numero_corte, max_tags=7)
    tags_kwai = filtrar_hashtags_dinamicas(nicho, artista, tema, "kwai", numero_corte, max_tags=7)

    shorts_desc = (
        f"Corte #{numero_corte:02d} | Trecho: {m_ini:02d}:{s_ini:02d} até {m_fim:02d}:{s_fim:02d} ({c_dur:.1f}s)\n\n"
        f"{desc_base}\n\n"
        f"{tags_shorts}"
    )

    # 3. Geração de Copy de TikTok Rotativa
    tiktok_pool = MODELOS_COPIES_TIKTOK.get(nicho, MODELOS_COPIES_TIKTOK["GERAL"])
    idx_tk = (numero_corte - 1) % len(tiktok_pool)
    tiktok_texto = tiktok_pool[idx_tk].format(artista=artista, tema=tema)
    tiktok_copy = f"Corte #{numero_corte:02d} 🎬 {tiktok_texto}\n\n{tags_tiktok}"

    # 4. Geração de Copy de Kwai Rotativa
    kwai_pool = MODELOS_COPIES_KWAI.get(nicho, MODELOS_COPIES_KWAI["GERAL"])
    idx_kw = (numero_corte - 1) % len(kwai_pool)
    kwai_texto = kwai_pool[idx_kw].format(artista=artista, tema=tema)
    kwai_copy = f"Corte #{numero_corte:02d} 📲 {kwai_texto}\n\n{tags_kwai}"

    # Ganchos de topo
    gancho_principal = f"{artista.upper()} - MOMENTO #{numero_corte:02d} DO SHOW!"
    opcoes_ganchos = [
        f"{shorts_titulo.replace('#Shorts', '').strip()}",
        f"VOCÊ NÃO VAI ACREDITAR NO QUE ROLOU! 😱",
        f"ESSE TRECHO É DE ARREPIAR! 💔 | {artista.upper()}",
        f"{artista.upper()} AO VIVO EM {tema.upper()}!"
    ]

    return {
        "nicho": nicho,
        "artista": artista,
        "tema": tema,
        "info_crop": info_crop,
        "gancho_principal": gancho_principal,
        "opcoes_ganchos": opcoes_ganchos,
        "shorts": {
            "titulo": shorts_titulo,
            "descricao": shorts_desc,
            "tags": tags_shorts
        },
        "tiktok": {
            "copy": tiktok_copy,
            "tags": tags_tiktok
        },
        "kwai": {
            "copy": kwai_copy,
            "tags": tags_kwai
        }
    }
