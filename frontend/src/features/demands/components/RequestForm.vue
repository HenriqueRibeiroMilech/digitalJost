<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
import FormField from '@/shared/components/FormField.vue'
import Button from '@/volt/Button.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import InputText from '@/volt/InputText.vue'
import Textarea from '@/volt/Textarea.vue'
import Select from '@/volt/Select.vue'
import Message from '@/volt/Message.vue'
import { demandsApi } from '../api'
import { entryOptions, urgencyOptions, fileAccept, fileSize } from '../presentation'
import type { RequestDetail, RequestFields } from '../types'

const props = defineProps<{ request?: RequestDetail }>()
const emit = defineEmits<{
  saved: [request: RequestDetail]
  busy: [value: boolean]
  cancel: []
  inspect: []
}>()
function initialFields(): RequestFields {
  return {
    entry_kind: props.request?.entry_kind ?? 'demanda',
    title: props.request?.title ?? '', description: props.request?.description ?? '',
    urgency: (props.request?.urgency as RequestFields['urgency']) ?? 'Média',
    contributor_id: props.request?.contributor_id ?? null,
    assumptions: props.request?.assumptions ?? '',
    current_problems: props.request?.current_problems ?? '',
    expected_benefits: props.request?.expected_benefits ?? '',
  }
}
const fields = reactive(initialFields())
const errorKeys = ['entry_kind', 'title', 'description', 'urgency', 'contributor_id',
  'assumptions', 'current_problems', 'expected_benefits', 'files', 'row_version'] as const
type ErrorField = typeof errorKeys[number]
const errors = reactive(Object.fromEntries(errorKeys.map(key => [key, ''])) as Record<ErrorField, string>)
const saving = ref(false)
const uncertain = ref(false)
const locked = computed(() => saving.value || uncertain.value)
const serverError = ref('')
const files = ref<File[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const formElement = ref<HTMLFormElement | null>(null)
const submissionKey = ref(crypto.randomUUID())
const formId = props.request ? `request-edit-${props.request.id}` : 'request-new'
// URL servida pelo Flask; o binding evita convertê-la em import de asset pelo Vite.
const flowExampleUrl = '/static/images/FLUXO.PNG'
const isError = computed(() => fields.entry_kind === 'erro')
const totalBytes = computed(() => files.value.reduce((sum, file) => sum + file.size, 0))
const detailFields = [
  { key: 'assumptions', label: 'Premissas da demanda *', placeholder: 'Quais condições e dependências precisam ser consideradas?' },
  { key: 'current_problems', label: 'Problemas atuais *', placeholder: 'Como o processo funciona hoje e quais dificuldades existem?' },
  { key: 'expected_benefits', label: 'Ganhos esperados *', placeholder: 'Que resultados esta demanda deve trazer?' },
] as const
const { data: contributors, isPending: contributorsLoading, isError: contributorsFailed, refetch } = useQuery({
  queryKey: ['demands', 'contributors'], queryFn: demandsApi.contributors,
  retry: false, refetchOnWindowFocus: false, refetchOnReconnect: false,
})
const contributorOptions = computed(() => {
  const items = contributors.value?.items ?? []
  if (props.request?.contributor_id && !items.some(item => item.id === props.request?.contributor_id)) {
    return [...items, { id: props.request.contributor_id, name: props.request.contributor_name ?? 'Contribuinte atual' }]
  }
  return items
})
watch(saving, value => emit('busy', value), { flush: 'sync' })

function selectFiles(event: Event) {
  const input = event.target as HTMLInputElement
  files.value = [...files.value, ...Array.from(input.files ?? [])]
  input.value = ''
  validateFiles()
}

function validateFiles() {
  if (props.request) return
  const allowed = fileAccept.split(',')
  errors.files = files.value.length < 1 || files.value.length > 10
    ? 'Adicione entre 1 e 10 documentos ou evidências.'
    : files.value.some(file => !allowed.includes('.' + (file.name.split('.').pop() ?? '').toLowerCase()))
      ? 'Selecione documentos ou imagens nos formatos permitidos.'
      : files.value.some(file => file.size === 0 || file.size > 10 * 1024 * 1024)
        ? 'Cada arquivo deve ter conteúdo e até 10 MB.'
        : totalBytes.value > 40 * 1024 * 1024 ? 'Use até 40 MB no total.' : ''
}

function clearDraft() {
  if (locked.value) return
  Object.assign(fields, initialFields())
  files.value = []
  errorKeys.forEach(key => { errors[key] = '' })
  serverError.value = ''
  submissionKey.value = crypto.randomUUID()
}

async function focusError() {
  await nextTick()
  formElement.value?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus()
}

async function submit() {
  if (saving.value) return
  errorKeys.forEach(key => { errors[key] = '' })
  serverError.value = ''
  errors.title = fields.title.trim().length < 1 ? 'Informe o título.' : ''
  errors.description = fields.description.trim().length < 1 ? 'Descreva sua necessidade ou o erro encontrado.' : ''
  if (!isError.value) {
    detailFields.forEach(({ key }) => { errors[key] = fields[key]?.trim() ? '' : 'Preencha este campo.' })
  }
  validateFiles()
  if (errorKeys.some(key => errors[key])) { await focusError(); return }
  const payload: RequestFields = {
    ...fields, title: fields.title.trim(), description: fields.description.trim(),
    assumptions: isError.value ? null : fields.assumptions?.trim() || null,
    current_problems: isError.value ? null : fields.current_problems?.trim() || null,
    expected_benefits: isError.value ? null : fields.expected_benefits?.trim() || null,
  }
  saving.value = true
  let saved: RequestDetail | undefined
  try {
    saved = props.request
      ? await demandsApi.update(props.request.id, { ...payload, row_version: props.request.row_version })
      : await demandsApi.create({ ...payload, submission_key: submissionKey.value }, files.value)
    uncertain.value = false
    if (!props.request) {
      Object.assign(fields, initialFields())
      files.value = []
      submissionKey.value = crypto.randomUUID()
    }
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      Object.assign(errors, validationMessages(error.detail, errorKeys))
      await focusError()
    }
    // Mantém o mesmo conteúdo/chave em uma repetição de criação incerta.
    uncertain.value = !props.request && error instanceof ApiError
      && (error.status === 0 || error.status >= 500 || (error.status >= 200 && error.status < 300))
    serverError.value = error instanceof Error ? error.message : 'Não foi possível salvar a solicitação.'
  } finally {
    saving.value = false
  }
  if (saved) emit('saved', saved)
}
</script>

<template>
  <form ref="formElement" novalidate :aria-busy="saving" @submit.prevent="submit">
    <div class="mb-6 rounded-2xl border border-dj-border bg-dj-canvas p-4 text-sm leading-6 text-dj-muted">
      <p>Conte o que você precisa. A equipe analisará as informações antes de definir a execução.</p>
      <p class="mt-1 text-xs">Campos com * são obrigatórios.</p>
    </div>
    <fieldset class="min-w-0 rounded-2xl border border-dj-border p-4 sm:p-6">
      <legend class="px-2 text-xs font-semibold tracking-wide text-dj-muted uppercase">Dados principais</legend>
      <div class="grid gap-5 md:grid-cols-3">
        <FormField :id="formId + '-entry_kind'" v-slot="{ controlProps }" label="O que deseja fazer? *" :error="errors.entry_kind">
          <Select v-model="fields.entry_kind" :input-id="controlProps.id" :options="entryOptions" option-label="label" option-value="value"
            :invalid="controlProps.invalid" :pt:label:aria-describedby="controlProps['aria-describedby']" pt:label:aria-required="true"
            :disabled="locked" class="w-full" pt:root:class="rounded-xl" />
        </FormField>
        <FormField :id="formId + '-urgency'" v-slot="{ controlProps }" label="Nível de urgência *" :error="errors.urgency">
          <Select v-model="fields.urgency" :input-id="controlProps.id" :options="urgencyOptions" :invalid="controlProps.invalid"
            :pt:label:aria-describedby="controlProps['aria-describedby']" pt:label:aria-required="true" :disabled="locked" class="w-full" pt:root:class="rounded-xl" />
        </FormField>
        <FormField :id="formId + '-contributor_id'" v-slot="{ controlProps }" label="Contribuinte (opcional)" :error="errors.contributor_id">
          <Select v-model="fields.contributor_id" :input-id="controlProps.id" :options="contributorOptions" option-label="name" option-value="id"
            filter show-clear placeholder="Sem contribuinte" :loading="contributorsLoading" :disabled="locked || contributorsLoading || contributorsFailed"
            :invalid="controlProps.invalid" :pt:label:aria-describedby="controlProps['aria-describedby']" class="w-full" pt:root:class="rounded-xl"
            empty-message="Nenhuma pessoa disponível" empty-filter-message="Nenhuma pessoa encontrada" />
          <p class="mt-2 text-xs leading-5 text-dj-muted">Também poderá consultar esta solicitação.</p>
        </FormField>
      </div>
      <Message v-if="contributorsFailed" severity="warn" class="mt-3">
        Não foi possível carregar os contribuintes. Você pode enviar sem contribuinte ou
        <SecondaryButton type="button" label="Tentar novamente" text :disabled="locked" @click="refetch()" />.
      </Message>
      <FormField :id="formId + '-title'" v-slot="{ controlProps }" label="Título *" :error="errors.title" class="mt-5">
        <InputText v-bind="controlProps" v-model="fields.title" required :maxlength="250" :disabled="locked"
          placeholder="Resuma sua solicitação em uma frase" pt:root:class="w-full rounded-xl py-3" />
      </FormField>
      <FormField :id="formId + '-description'" v-slot="{ controlProps }" :label="isError ? 'Descrição do erro *' : 'Objetivo da demanda *'"
        :error="errors.description" class="mt-5">
        <Textarea v-bind="controlProps" v-model="fields.description" required :rows="5" :maxlength="4000" :disabled="locked"
          :placeholder="isError ? 'Informe onde ocorreu, os passos para reproduzir, o resultado esperado e o que aconteceu.' : 'Explique o que precisa ser feito e qual é o objetivo.'"
          pt:root:class="w-full rounded-xl" />
      </FormField>
      <p class="mt-1 text-right text-xs text-dj-muted">{{ fields.description.length }} / 4.000</p>
    </fieldset>
    <fieldset v-show="!isError" class="mt-6 min-w-0 rounded-2xl border border-dj-border p-4 sm:p-6">
      <legend class="px-2 text-xs font-semibold tracking-wide text-dj-muted uppercase">Entenda o cenário</legend>
      <div class="grid gap-5 lg:grid-cols-3">
        <FormField v-for="field in detailFields" :id="formId + '-' + field.key" :key="field.key" v-slot="{ controlProps }" :label="field.label" :error="errors[field.key]">
          <Textarea v-bind="controlProps" v-model="fields[field.key]" :required="!isError" :rows="6" :maxlength="4000"
            :disabled="locked" :placeholder="field.placeholder" pt:root:class="w-full rounded-xl" />
          <p class="mt-1 text-right text-xs text-dj-muted">{{ fields[field.key]?.length ?? 0 }} / 4.000</p>
        </FormField>
      </div>
    </fieldset>
    <fieldset v-if="!request" class="mt-6 min-w-0 rounded-2xl border border-dj-border p-4 sm:p-6">
      <legend class="px-2 text-xs font-semibold tracking-wide text-dj-muted uppercase">{{ isError ? 'Evidências do erro' : 'Documentos e fluxo' }}</legend>
      <div class="grid items-start gap-6" :class="{ 'lg:grid-cols-2': !isError }">
        <div class="min-w-0">
          <p class="mb-4 text-sm leading-6 text-dj-muted">{{ isError ? 'Anexe uma imagem ou documento que ajude a entender o erro.' : 'Anexe documentos que representem o fluxo e facilitem a análise da demanda.' }}</p>
          <FormField :id="formId + '-files'" label="Documentos *" :error="errors.files">
            <input :id="formId + '-files'" ref="fileInput" type="file" multiple :accept="fileAccept" :disabled="locked"
              :aria-invalid="Boolean(errors.files)" :aria-describedby="formId + '-file-help' + (errors.files ? ' ' + formId + '-files-error' : '')"
              class="block w-full rounded-xl border border-dashed border-dj-border bg-dj-canvas p-4 text-sm text-dj-muted file:mr-4 file:cursor-pointer file:rounded-lg file:border-0 file:bg-dj-brand file:px-4 file:py-2 file:text-white"
              @change="selectFiles" />
          </FormField>
          <p :id="formId + '-file-help'" class="mt-3 text-xs leading-5 text-dj-muted">Até 10 arquivos, 10 MB por arquivo e 40 MB no total. Word, Excel, PowerPoint, PDF, texto e imagens.</p>
          <ul v-if="files.length" class="mt-4 divide-y divide-dj-border" aria-label="Documentos selecionados">
            <li v-for="(file, index) in files" :key="index" class="flex items-center justify-between gap-3 py-2">
              <span class="min-w-0 break-words text-sm">{{ file.name }} <span class="text-xs text-dj-muted">({{ fileSize(file.size) }})</span></span>
              <SecondaryButton type="button" icon="pi pi-times" text :aria-label="'Remover ' + file.name" :disabled="locked"
                pt:root:class="size-10 shrink-0 rounded-xl" @click="files.splice(index, 1); validateFiles()" />
            </li>
          </ul>
        </div>
        <figure v-if="!isError" class="min-w-0 rounded-2xl border border-dj-border bg-dj-canvas p-3">
          <a :href="flowExampleUrl" target="_blank" rel="noopener noreferrer" class="block rounded-xl"
            aria-label="Abrir exemplo de fluxo em tamanho original (abre em outra aba)">
            <img :src="flowExampleUrl" alt="Exemplo de fluxo para detalhar uma demanda"
              class="block max-h-80 w-full rounded-xl object-contain" />
          </a>
          <figcaption class="mt-3 text-center text-xs leading-5 text-dj-muted">Exemplo de fluxo da demanda</figcaption>
        </figure>
      </div>
    </fieldset>
    <Message v-if="serverError" severity="error" class="mt-5" role="alert">{{ serverError }}</Message>
    <Message v-if="uncertain" severity="warn" class="mt-3">
      Confira Minhas solicitações antes de iniciar outro cadastro. Você também pode confirmar este envio novamente; os mesmos dados serão reconhecidos sem criar uma duplicata.
    </Message>
    <div class="mt-6 flex flex-wrap justify-end gap-3 border-t border-dj-border pt-5">
      <SecondaryButton v-if="!request" type="button" label="Limpar formulário" outlined :disabled="locked" @click="clearDraft" />
      <SecondaryButton v-if="request" type="button" label="Cancelar edição" outlined :disabled="saving" @click="emit('cancel')" />
      <SecondaryButton v-if="uncertain" type="button" label="Conferir minhas solicitações" outlined :disabled="saving" @click="emit('inspect')" />
      <Button type="submit" :label="saving ? 'Enviando…' : request ? 'Salvar alterações' : uncertain ? 'Confirmar envio novamente' : 'Enviar solicitação'"
        icon="pi pi-send" :loading="saving" :disabled="saving" pt:root:class="rounded-xl px-6 py-3" />
    </div>
  </form>
</template>
