<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
import AppDialog from '@/shared/components/AppDialog.vue'
import FormField from '@/shared/components/FormField.vue'
import Button from '@/volt/Button.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import Select from '@/volt/Select.vue'
import InputText from '@/volt/InputText.vue'
import Textarea from '@/volt/Textarea.vue'
import Message from '@/volt/Message.vue'
import { demandsApi, workApi } from '../api'
import { fileAccept, fileSize, noticeInputTime, urgencyOptions, workKindOptions } from '../presentation'
import type { WorkCreate, WorkDetail, WorkKind } from '../types'

const props = defineProps<{ ownerId?: string | null; work?: WorkDetail }>()
const emit = defineEmits<{
  closed: []; busy: [value: boolean]; saved: [item: WorkDetail]; inspect: [kind: WorkKind, owner: string]; uncertain: []
}>()
const visible = ref(true)
const saving = ref(false)
const uncertain = ref(false)
const locked = computed(() => saving.value || uncertain.value)
const kind = ref<WorkKind | null>(props.work?.kind ?? null)
const fields = reactive({ title: props.work?.title ?? '', description: props.work?.description ?? '', responsible_id: props.work?.responsible_id ?? props.ownerId ?? null,
  contributor_id: props.work?.contributor_id ?? null, urgency: (props.work?.urgency ?? 'Média') as 'Alta' | 'Média' | 'Baixa',
  assumptions: props.work?.assumptions ?? '', current_problems: props.work?.current_problems ?? '', expected_benefits: props.work?.expected_benefits ?? '',
  starts_at: noticeInputTime(props.work?.starts_at ?? null), ends_at: noticeInputTime(props.work?.ends_at ?? null), hide_after_end: props.work?.hide_after_end ?? true })
const key = crypto.randomUUID()
const files = ref<File[]>([])
const form = ref<HTMLFormElement | null>(null)
const serverError = ref('')
const errorKeys = ['kind', 'title', 'description', 'responsible_id', 'contributor_id', 'urgency',
  'assumptions', 'current_problems', 'expected_benefits', 'starts_at', 'ends_at', 'hide_after_end', 'files', 'submission_key', 'row_version'] as const
const errors = reactive(Object.fromEntries(errorKeys.map(field => [field, ''])) as Record<typeof errorKeys[number], string>)
const complex = computed(() => kind.value !== null && !['atividade', 'aviso'].includes(kind.value))
const context = computed(() => kind.value === 'projeto' || kind.value === 'melhoria')
const contextFields = [
  { key: 'assumptions', label: 'Premissas' }, { key: 'current_problems', label: 'Problemas atuais' },
  { key: 'expected_benefits', label: 'Ganhos esperados' },
] as const
const owners = useQuery({ queryKey: ['demands', 'management', 'responsibles'], queryFn: demandsApi.responsibles,
  retry: false, refetchOnWindowFocus: false, refetchOnReconnect: false })
const contributors = useQuery({ queryKey: ['demands', 'contributors'], queryFn: demandsApi.contributors,
  enabled: complex, retry: false, refetchOnWindowFocus: false, refetchOnReconnect: false })
const ownerOptions = computed(() => {
  const items = owners.data.value?.items ?? []
  return props.work && !items.some(person => person.id === props.work?.responsible_id)
    ? [...items, { id: props.work.responsible_id, name: props.work.responsible_name ?? 'Responsável atual' }] : items
})
const contributorOptions = computed(() => {
  const items = (contributors.data.value?.items ?? []).filter(person => !props.work || person.id !== props.work.requester_id)
  return props.work?.contributor_id && !items.some(person => person.id === props.work?.contributor_id)
    ? [...items, { id: props.work.contributor_id, name: props.work.contributor_name ?? 'Contribuinte atual' }] : items
})
watch(saving, value => emit('busy', value), { flush: 'sync' })
watch(owners.data, result => {
  if (result && fields.responsible_id && fields.responsible_id !== props.work?.responsible_id && !result.items.some(person => person.id === fields.responsible_id)) {
    fields.responsible_id = null
  }
}, { immediate: true })

function close() { if (!saving.value) visible.value = false }
function selectFiles(event: Event) {
  const input = event.target as HTMLInputElement
  files.value = [...files.value, ...Array.from(input.files ?? [])]
  input.value = ''
}
function time(value: string) {
  const date = value ? new Date(value) : null
  return date && !Number.isNaN(date.getTime()) ? date.toISOString() : null
}
async function focusError() {
  await nextTick()
  form.value?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus()
}
async function submit() {
  if (saving.value || (props.work && uncertain.value)) return
  errorKeys.forEach(field => { errors[field] = '' })
  serverError.value = ''
  if (!kind.value) errors.kind = 'Selecione o tipo do cadastro.'
  if (!fields.title.trim()) errors.title = 'Informe o título.'
  if (!fields.description.trim()) errors.description = 'Informe a descrição.'
  if (!fields.responsible_id) errors.responsible_id = 'Selecione o responsável.'
  if (context.value) contextFields.forEach(field => { if (!fields[field.key].trim()) errors[field.key] = 'Preencha este campo.' })
  const starts = kind.value === 'aviso' ? time(fields.starts_at) : null
  const ends = kind.value === 'aviso' ? time(fields.ends_at) : null
  if (kind.value === 'aviso') {
    if (!starts) errors.starts_at = 'Informe a data e hora de início.'
    if (!ends || (starts && ends <= starts)) errors.ends_at = 'Informe um fim posterior ao início.'
  }
  const selectedFiles = complex.value && !props.work ? files.value : []
  const allowed = fileAccept.split(',')
  if (selectedFiles.length > 10 || selectedFiles.some(file => file.size === 0 || file.size > 10 * 1024 * 1024
    || !allowed.includes('.' + (file.name.split('.').pop() ?? '').toLowerCase()))
    || selectedFiles.reduce((sum, file) => sum + file.size, 0) > 40 * 1024 * 1024) {
    errors.files = 'Use até 10 documentos permitidos, com conteúdo, até 10 MB por arquivo e 40 MB no total.'
  }
  if (errorKeys.some(field => errors[field]) || !kind.value || !fields.responsible_id) { await focusError(); return }
  const payload: WorkCreate = {
    kind: kind.value, title: fields.title.trim(), description: fields.description.trim(), responsible_id: fields.responsible_id,
    contributor_id: complex.value ? fields.contributor_id : null, urgency: complex.value ? fields.urgency : null,
    assumptions: context.value ? fields.assumptions.trim() : null,
    current_problems: context.value ? fields.current_problems.trim() : null,
    expected_benefits: context.value ? fields.expected_benefits.trim() : null,
    starts_at: starts, ends_at: ends, hide_after_end: kind.value === 'aviso' ? fields.hide_after_end : false, submission_key: key,
  }
  saving.value = true
  let saved: WorkDetail | undefined
  try {
    if (props.work) {
      const { submission_key: _key, ...content } = payload
      saved = await workApi.updateContent(props.work.id, { ...content, row_version: props.work.row_version })
    } else saved = await workApi.create(payload, selectedFiles)
    uncertain.value = false
  } catch (error) {
    serverError.value = error instanceof Error ? error.message : 'Não foi possível cadastrar.'
    if (error instanceof ApiError) {
      Object.assign(errors, validationMessages(error.detail, errorKeys))
      uncertain.value = uncertain.value || error.status === 0 || error.status === 409 || error.status >= 500
        || (error.status >= 200 && error.status < 300)
    } else uncertain.value = true
    if (props.work && uncertain.value) emit('uncertain')
  } finally { saving.value = false }
  if (saved) { emit('saved', saved); close() }
  else await focusError()
}
function inspect() {
  if (saving.value || !kind.value || !fields.responsible_id) return
  emit('inspect', kind.value, fields.responsible_id)
  close()
}
</script>

<template>
  <AppDialog id="work-create-dialog" :visible="visible" :title="work ? 'Editar dados e responsável' : 'Nova demanda ou aviso'"
    :subtitle="work ? work.source_request_id ? 'Atualize o trabalho da equipe. Os dados enviados na solicitação original serão preservados.' : 'Atualize o conteúdo e as pessoas deste registro.' : 'Escolha o tipo e preencha as informações do cadastro.'"
    :icon="work ? 'pi pi-pencil' : 'pi pi-plus'" :busy="saving" :initial-focus-id="work ? 'work-create-title' : 'work-create-kind'" @update:visible="close" @closed="emit('closed')">
    <form id="work-create-form" ref="form" class="space-y-4" novalidate @submit.prevent="submit">
      <Message v-if="serverError" severity="error" role="alert">{{ serverError }}</Message>
      <Message v-if="uncertain" severity="warn" role="status">{{ work ? 'Feche esta edição e recarregue os detalhes para conferir o resultado antes de salvar novamente.' : 'O resultado do envio precisa ser conferido. Você pode confirmar o mesmo envio sem alterar os dados ou fechar para consultar o quadro antes de iniciar outro cadastro.' }}</Message>
      <FormField v-if="!work" id="work-create-kind" label="Tipo *" :error="errors.kind" v-slot="{ controlProps }">
        <Select v-model="kind" :input-id="controlProps.id" :invalid="controlProps.invalid" :options="workKindOptions" option-label="label" option-value="value"
          :pt:label:aria-describedby="controlProps['aria-describedby']" pt:label:aria-required="true" :disabled="locked" placeholder="Projeto, Melhoria, Erro, Atividade ou Aviso" class="w-full" />
      </FormField>
      <template v-if="kind">
        <div class="grid gap-3 sm:grid-cols-2">
          <FormField id="work-create-title" label="Título *" :error="errors.title" v-slot="{ controlProps }">
            <InputText v-model="fields.title" v-bind="controlProps" required :maxlength="250" :disabled="locked" class="w-full" />
          </FormField>
          <FormField id="work-create-responsible" label="Responsável *" :error="errors.responsible_id" v-slot="{ controlProps }">
            <Select v-model="fields.responsible_id" :input-id="controlProps.id" :invalid="controlProps.invalid" :options="ownerOptions"
              option-label="name" option-value="id" filter :loading="owners.isPending.value" :disabled="locked || owners.isPending.value || owners.isError.value"
              :pt:label:aria-describedby="controlProps['aria-describedby']" pt:label:aria-required="true" placeholder="Selecione o responsável" class="w-full" />
          </FormField>
        </div>
        <Message v-if="owners.isError.value" severity="error">Não foi possível carregar os responsáveis.
          <SecondaryButton type="button" label="Tentar novamente" :disabled="locked" @click="owners.refetch()" />
        </Message>
        <p v-else-if="!owners.isPending.value && !owners.data.value?.items.length" class="text-sm text-dj-muted">Nenhum responsável ativo disponível na equipe.</p>
        <FormField id="work-create-description" :label="kind === 'erro' ? 'Descrição do erro *' : kind === 'aviso' || kind === 'atividade' ? 'Descrição *' : 'Objetivo da demanda *'"
          :error="errors.description" v-slot="{ controlProps }">
          <Textarea v-model="fields.description" v-bind="controlProps" required :rows="3" :maxlength="4000" :disabled="locked" class="w-full" />
        </FormField>
        <div v-if="complex" class="grid gap-3 sm:grid-cols-2">
          <FormField id="work-create-urgency" label="Urgência *" :error="errors.urgency" v-slot="{ controlProps }">
            <Select v-model="fields.urgency" :input-id="controlProps.id" :invalid="controlProps.invalid" :options="urgencyOptions" :disabled="locked"
              :pt:label:aria-describedby="controlProps['aria-describedby']" pt:label:aria-required="true" class="w-full" />
          </FormField>
          <FormField id="work-create-contributor" label="Contribuinte (opcional)" :error="errors.contributor_id" v-slot="{ controlProps }">
            <Select v-model="fields.contributor_id" :input-id="controlProps.id" :invalid="controlProps.invalid" :options="contributorOptions"
              option-label="name" option-value="id" filter show-clear :disabled="locked || contributors.isPending.value || contributors.isError.value"
              :loading="contributors.isPending.value" :pt:label:aria-describedby="controlProps['aria-describedby']" placeholder="Sem contribuinte" class="w-full" />
          </FormField>
        </div>
        <Message v-if="complex && contributors.isError.value" severity="warn">Não foi possível carregar os contribuintes.
          <SecondaryButton type="button" label="Tentar novamente" :disabled="locked" @click="contributors.refetch()" />
        </Message>
        <div v-if="context" class="grid gap-3 lg:grid-cols-3">
          <FormField v-for="field in contextFields" :key="field.key" :id="'work-create-' + field.key" :label="field.label + ' *'"
            :error="errors[field.key]" v-slot="{ controlProps }">
            <Textarea v-model="fields[field.key]" v-bind="controlProps" required :rows="3" :maxlength="4000" :disabled="locked" class="w-full" />
          </FormField>
        </div>
        <div v-if="kind === 'aviso'" class="grid gap-3 sm:grid-cols-2">
          <FormField id="work-create-starts" label="Data e hora de início *" :error="errors.starts_at" v-slot="{ controlProps }">
            <InputText v-model="fields.starts_at" v-bind="controlProps" required type="datetime-local" step="0.001" :disabled="locked" class="w-full" />
          </FormField>
          <FormField id="work-create-ends" label="Data e hora de fim *" :error="errors.ends_at" v-slot="{ controlProps }">
            <InputText v-model="fields.ends_at" v-bind="controlProps" required type="datetime-local" step="0.001" :disabled="locked" class="w-full" />
          </FormField>
          <label class="flex items-center gap-2 text-sm sm:col-span-2">
            <input v-model="fields.hide_after_end" type="checkbox" :disabled="locked" class="size-4 accent-dj-brand" /> Ocultar do mural após o fim
          </label>
          <p class="text-xs text-dj-muted sm:col-span-2">Informe os horários locais. Avisos vencidos e finalizados continuam disponíveis nos filtros do mural.</p>
        </div>
        <FormField v-if="complex && !work" id="work-create-files" label="Documentos e evidências (opcional)" :error="errors.files" v-slot="{ controlProps }">
          <input v-bind="controlProps" type="file" multiple :accept="fileAccept" :disabled="locked"
            class="block w-full rounded-xl border border-dj-border p-3 text-sm" @change="selectFiles" />
          <p class="mt-2 text-xs leading-5 text-dj-muted">Até 10 documentos ou imagens; 10 MB por arquivo e 40 MB no total.</p>
          <ul v-if="files.length" class="mt-3 space-y-2 text-sm">
            <li v-for="(file, index) in files" :key="index" class="flex items-center justify-between gap-3 rounded-lg bg-dj-canvas p-2">
              <span class="min-w-0 break-words">{{ file.name }} ({{ fileSize(file.size) }})</span>
              <SecondaryButton type="button" icon="pi pi-times" :aria-label="'Remover ' + file.name" :disabled="locked" @click="files.splice(index, 1)" />
            </li>
          </ul>
        </FormField>
      </template>
    </form>
    <template #footer>
      <Button type="submit" form="work-create-form" :label="work ? 'Salvar alterações' : uncertain ? 'Confirmar mesmo envio' : kind === 'aviso' ? 'Criar aviso' : 'Criar demanda'"
        :loading="saving" :disabled="saving || (Boolean(work) && uncertain) || !kind || owners.isPending.value || owners.isError.value || !ownerOptions.length" />
      <SecondaryButton v-if="uncertain && !work" type="button" label="Fechar e conferir quadro" :disabled="saving" @click="inspect" />
      <SecondaryButton v-else type="button" :label="uncertain ? 'Fechar' : 'Cancelar'" outlined :disabled="saving" @click="close" />
    </template>
  </AppDialog>
</template>
