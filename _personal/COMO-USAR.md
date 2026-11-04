# Área /personal: agenda dos pacotes

Esta pasta (`_personal/`) não é publicada no site porque começa com `_`. Atenção: o repositório é público, então ela fica visível para quem abrir o repo no GitHub.

- Configuração: `_personal/alunos.json`
- Gerador: `scripts/agenda_personal.py`, que cria `personal/dados/<slug>.json` e `personal/<slug>/index.html`
- Modelo da página: `personal/aluno.html`. Edite só ele; as cópias são refeitas pelo gerador.
- Automação: `.github/workflows/agenda-personal.yml`, todo dia às 21h17 de Brasília. Também dá para rodar à mão em Actions → "Agenda personal" → Run workflow.

## Configurar uma vez: conta de serviço do Google

1. Entre em https://console.cloud.google.com com a conta aldemirjrpersonal@gmail.com e crie um projeto (ex.: `ajr-agenda`).
2. Vá em **APIs e serviços → Biblioteca**, procure **Google Calendar API** e clique em **Ativar**.
3. Vá em **IAM e administrador → Contas de serviço → Criar conta de serviço**. Use o nome `agenda-site`. Não precisa dar papel nenhum. Clique em **Concluir**.
4. Abra a conta criada, vá na aba **Chaves → Adicionar chave → Criar nova chave → JSON**. Um arquivo `.json` vai ser baixado. Guarde esse arquivo fora da pasta do site e nunca coloque no repositório.
5. Copie o e-mail da conta de serviço (algo como `agenda-site@ajr-agenda.iam.gserviceaccount.com`).
6. No Google Agenda (web), vá na engrenagem → **Configurações**, escolha a agenda *aldemirjrpersonal@gmail.com* → **Compartilhar com pessoas e grupos específicos → Adicionar pessoas**. Cole o e-mail da conta de serviço e escolha a permissão **"Ver todos os detalhes do evento"**.
7. No GitHub, abra o repo `ajrperformance/ajr-site` → **Settings → Secrets and variables → Actions → New repository secret**.
   - Nome: `GOOGLE_SERVICE_ACCOUNT_JSON`
   - Valor: o conteúdo inteiro do arquivo `.json` baixado.
   - Depois de salvar, apague o arquivo `.json` do Downloads.
8. Teste em **Actions → Agenda personal → Run workflow**. Se der certo, fica verde.

**Aviso de falha por e-mail.** O GitHub manda e-mail para quem fez a última alteração no cron do workflow. Confira em github.com → foto → **Settings → Notifications → Actions** se a opção "Email" está marcada e "Only notify for failed workflows" está ligada.

O GitHub pausa workflows agendados de repositórios sem nenhuma atividade por 60 dias. Se isso acontecer, vá em Actions e clique em "Enable workflow".

## Adicionar um aluno novo

1. Crie o slug: nome do aluno em minúsculas, sem acento, com hífens, mais 8 letras/números aleatórios. Ex.: `joao-pedro-3fq8z1mk`. Para gerar o código, rode no Terminal:
   `python3 -c "import secrets,string;a=string.ascii_lowercase+string.digits;print(''.join(secrets.choice(a) for _ in range(8)))"`
2. Acrescente um item em `alunos` no `_personal/alunos.json`:
   ```json
   {
     "nome": "João Pedro",
     "slug": "joao-pedro-3fq8z1mk",
     "filtro": "João Pedro",
     "local": "Clínica Vitallitè",
     "horarios": "Terças e quintas 18h",
     "dias_fixos": ["ter", "qui"],
     "pacote_inicio": "2026-11-10",
     "total": 12,
     "historico": { "conferido_ate": "2026-11-09", "aulas": [], "remarcadas": [] }
   }
   ```
   - O `filtro` é o texto que aparece no título do evento na agenda, sem diferença entre maiúsculas e acentos. Use um nome que não pegue outro aluno (ex.: "Ana Claudia" não pega "Ana Laura").
   - `conferido_ate` é o dia anterior ao início do pacote, quando não há nada conferido ainda.
3. Publique (`scripts/publicar.sh "Novo aluno"`) e rode o workflow à mão. O link do aluno fica `https://ajrperformance.com.br/personal/<slug>/`.

## Renovar um pacote (mesmo link)

No item do aluno, mantenha o `slug` (assim o link continua o mesmo) e mude:
- `pacote_inicio`: dia da 1ª aula do novo pacote;
- `historico`: `{ "conferido_ate": "<dia anterior ao novo início>", "aulas": [], "remarcadas": [] }`;
- `total`, se o novo pacote tiver outro tamanho.

Depois publique e rode o workflow.

Se quiser trocar o link (ex.: o aluno repassou para alguém), troque o código de 8 caracteres do slug. O gerador apaga a página antiga sozinho.

## Remover um aluno

Apague o item dele do `alunos.json`, publique e rode o workflow. A página e o JSON dele são apagados.

## Regras que o gerador aplica (só para eventos depois de `conferido_ate`)

- Ignora eventos com status `cancelled` e títulos que não contêm o filtro.
- Check-in `[check-in] não aconteceu · ...` ou título começando com `X `: o evento não conta como aula e entra em remarcadas. O motivo vira "feriado", "imprevisto do professor", "desmarcada pela aluna" ou só "remarcada". O texto literal nunca é exibido.
- `[check-in] realizada`, ou evento que já terminou sem "não aconteceu": conta como feita.
- Evento futuro: agendada, com horário.
- Aula em dia fora de `dias_fixos` (evento movido ou avulso): recebe a observação "reposição".
- Uma aula por data, até completar o `total`, em ordem de data. A data de vencimento é a da última aula do pacote.
- O JSON só é regravado (e commitado) quando algo muda. O "Atualizado em" mostra a última mudança.
