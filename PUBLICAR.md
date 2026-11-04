# Como publicar alterações no site

O site (ajrperformance.com.br) é publicado pelo GitHub Pages a partir da branch `main`.

1. Coloque o token pessoal do GitHub num arquivo `.github-token` na raiz da pasta do site. Ele está no `.gitignore` e nunca é enviado.
2. Na pasta do site, rode:

   ```bash
   scripts/publicar.sh "Descrição da alteração"
   ```

3. O script faz `git add -A`, `git commit` com a sua mensagem e `git push` para a `main` usando o token.
   - O token não é gravado no `.git/config` nem no Keychain, e não aparece no terminal.
   - Se `.github-token` estiver no stage, o envio é cancelado.
   - Só funciona na branch `main`. Se o push for recusado, rode `git pull origin main` e tente de novo.
4. Em cerca de 1 minuto a alteração aparece no site.
