"use client";

import { Button } from "@/components/ui/Button";
import {
  Dialog,
  DialogClose,
  DialogFooter,
  DialogHeader,
  DialogPanel,
  DialogPopup,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

const triggerClassName =
  "cursor-pointer text-sm text-zinc-400 transition-colors hover:text-white";

function TermsDialog() {
  return (
    <Dialog>
      <DialogTrigger className={triggerClassName}>Termos de Uso</DialogTrigger>
      <DialogPopup showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>Termos de Uso</DialogTitle>
        </DialogHeader>
        <DialogPanel>
          <div className="flex flex-col gap-4 [&_strong]:font-semibold [&_strong]:text-white">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Aceitação dos Termos</strong>
                </p>
                <p>
                  Ao acessar e utilizar este site, o usuário concorda em cumprir
                  e estar vinculado a estes Termos de Uso. Quem não concordar
                  com estes termos deve interromper o uso do site imediatamente.
                </p>
              </div>
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Responsabilidades da Conta</strong>
                </p>
                <p>
                  O usuário é responsável por manter a confidencialidade das
                  credenciais da conta. Quaisquer atividades realizadas sob a
                  conta são de responsabilidade exclusiva do titular. O usuário
                  deve notificar os administradores imediatamente em caso de
                  acesso não autorizado.
                </p>
              </div>
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Uso de Conteúdo e Restrições</strong>
                </p>
                <p>
                  O site e seu conteúdo original são protegidos por leis de
                  propriedade intelectual. É proibido reproduzir, distribuir,
                  modificar, criar obras derivadas ou explorar comercialmente
                  qualquer conteúdo sem autorização prévia e por escrito dos
                  titulares.
                </p>
              </div>
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Limitação de Responsabilidade</strong>
                </p>
                <p>
                  O site fornece conteúdo &ldquo;no estado em que se
                  encontra&rdquo;, sem garantias. Os titulares não serão
                  responsáveis por danos diretos, indiretos, incidentais,
                  consequenciais ou punitivos decorrentes do uso da plataforma.
                </p>
              </div>
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Diretrizes de Conduta</strong>
                </p>
                <ul className="list-disc pl-6">
                  <li>Não enviar conteúdo prejudicial ou malicioso</li>
                  <li>Respeitar os direitos de outros usuários</li>
                  <li>
                    Evitar atividades que possam comprometer o funcionamento do
                    site
                  </li>
                  <li>Cumprir as leis locais e internacionais aplicáveis</li>
                </ul>
              </div>
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Alterações nos Termos</strong>
                </p>
                <p>
                  Reservamo-nos o direito de modificar estes termos a qualquer
                  momento. O uso contínuo do site após as alterações constitui
                  aceitação dos novos termos.
                </p>
              </div>
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Rescisão</strong>
                </p>
                <p>
                  Podemos encerrar ou suspender o acesso do usuário sem aviso
                  prévio em caso de violação destes termos ou por qualquer outro
                  motivo considerado adequado pela administração.
                </p>
              </div>
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Legislação Aplicável</strong>
                </p>
                <p>
                  Estes termos são regidos pelas leis da República Federativa do
                  Brasil, sem consideração a princípios de conflito de leis.
                </p>
              </div>
            </div>
          </div>
        </DialogPanel>
        <DialogFooter>
          <DialogClose render={<Button variant="ghost" />}>Cancelar</DialogClose>
          <DialogClose render={<Button />}>Concordo</DialogClose>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}

function PrivacyDialog() {
  return (
    <Dialog>
      <DialogTrigger className={triggerClassName}>
        Política de Privacidade
      </DialogTrigger>
      <DialogPopup showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>Política de Privacidade</DialogTitle>
        </DialogHeader>
        <DialogPanel>
          <div className="flex flex-col gap-4 [&_strong]:font-semibold [&_strong]:text-white">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Coleta de Dados</strong>
                </p>
                <p>
                  Coletamos informações fornecidas voluntariamente, como nome,
                  e-mail e dados de contato, além de informações técnicas
                  necessárias para o funcionamento do serviço, como endereço IP,
                  tipo de navegador e páginas acessadas.
                </p>
              </div>
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Uso das Informações</strong>
                </p>
                <p>
                  Utilizamos os dados para prestar e melhorar nossos serviços,
                  processar solicitações, comunicar atualizações relevantes e
                  garantir a segurança da plataforma. Não vendemos dados
                  pessoais a terceiros.
                </p>
              </div>
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Compartilhamento de Dados</strong>
                </p>
                <p>
                  Podemos compartilhar informações com prestadores de serviço
                  essenciais à operação, sempre sob obrigações de
                  confidencialidade, ou quando exigido por lei, ordem judicial
                  ou autoridade competente.
                </p>
              </div>
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Armazenamento e Segurança</strong>
                </p>
                <p>
                  Adotamos medidas técnicas e organizacionais adequadas para
                  proteger os dados contra acesso não autorizado, alteração,
                  divulgação ou destruição. Nenhum método de transmissão pela
                  internet é totalmente seguro.
                </p>
              </div>
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Direitos do Titular</strong>
                </p>
                <ul className="list-disc pl-6">
                  <li>Confirmar a existência de tratamento de dados</li>
                  <li>Solicitar acesso, correção ou exclusão de dados</li>
                  <li>Revogar consentimento quando aplicável</li>
                  <li>Solicitar portabilidade dos dados, nos termos da LGPD</li>
                </ul>
              </div>
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Cookies e Tecnologias Semelhantes</strong>
                </p>
                <p>
                  Utilizamos cookies e tecnologias semelhantes para melhorar a
                  experiência de navegação, analisar o uso do site e lembrar
                  preferências. O usuário pode gerenciar cookies nas
                  configurações do navegador.
                </p>
              </div>
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Retenção de Dados</strong>
                </p>
                <p>
                  Mantemos os dados pelo tempo necessário para cumprir as
                  finalidades descritas nesta política, obrigações legais ou
                  resolução de disputas, eliminando-os de forma segura quando
                  não forem mais necessários.
                </p>
              </div>
              <div className="flex flex-col gap-1">
                <p>
                  <strong>Alterações nesta Política</strong>
                </p>
                <p>
                  Esta política pode ser atualizada periodicamente. A versão
                  vigente será sempre disponibilizada neste site, e o uso
                  contínuo após alterações implica ciência das novas condições.
                </p>
              </div>
            </div>
          </div>
        </DialogPanel>
        <DialogFooter>
          <DialogClose render={<Button variant="ghost" />}>Cancelar</DialogClose>
          <DialogClose render={<Button />}>Concordo</DialogClose>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-white/10 px-4 py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 text-center sm:flex-row sm:text-left">
        <div>
          <p className="text-sm font-semibold tracking-tight text-white">
            4<span className="text-brand">SEO</span>
          </p>
          <p className="mt-2 max-w-md text-sm text-zinc-500">
            Desenvolvido por 4Scale — Escalando seu negócio de forma
            inteligente.
          </p>
        </div>

        <nav aria-label="Links legais" className="flex items-center gap-6">
          <TermsDialog />
          <PrivacyDialog />
        </nav>
      </div>
    </footer>
  );
}
