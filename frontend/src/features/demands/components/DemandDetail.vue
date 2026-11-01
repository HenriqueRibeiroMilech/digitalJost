<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
import AppDialog from '@/shared/components/AppDialog.vue'
import FormField from '@/shared/components/FormField.vue'
import RequestState from '@/shared/components/RequestState.vue'
import Button from '@/volt/Button.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import Select from '@/volt/Select.vue'
import InputNumber from '@/volt/InputNumber.vue'
import Textarea from '@/volt/Textarea.vue'
import Message from '@/volt/Message.vue'
import Tag from '@/volt/Tag.vue'
import { workApi } from '../api'
import { displayDate, displayDay, fileSize, noticeStateLabel, planningLabels, statusLabel, workFieldLabels, workHistoryLabel, workHistoryValue, workKind } from '../presentation'
import type { WorkDetail, WorkPlanning } from '../types'
import DemandActions from './DemandActions.vue'
import DemandCreateDialog from './DemandCreateDialog.vue'
import DemandTasks from './DemandTasks.vue'

const props = defineProps<{ id: number }>()
const emit = defineEmits<{ closed: []; changed: []; busy: [value: boolean] }>()
const visible = ref(true)
const saving = ref(false)
const reloading = ref(false)
const actionSaving = ref(false)
const actionEditing = ref(false)
const editingContent = ref(false)
const taskBusy = ref(false)
const noticeConfirm = ref(false)
const reloadKey = ref(0)
const busy = computed(() => saving.value || reloading.value || actionSaving.value || editingContent.value || taskBusy.value || noticeConfirm.value)
const needsReload = ref(false)
const tab = ref<'info' | 'tasks' | 'history'>('info')
const serverError = ref('')
const feedback = ref('')
const form = ref<HTMLFormElement | null>(null)
const prefix = 'work-detail-' + props.id
const client = useQueryClient()
const queryKey = ['demands', 'work', 'detail', props.id]
const { data, isPending, isFetching, isError, error, refetch } = useQuery({ queryKey, queryFn: () => workApi.get(props.id),
  retry: false, refetchOnWindowFocus: false, refetchOnReconnect: false })
const plan = reactive<WorkPlanning>({ difficulty: null, priority: null, estimated_hours: null, daily_hours: null, completed_hours: 0, observations: null })
const completed = ref<number | null>(0)
const errorKeys = ['difficulty', 'priority', 'estimated_hours', 'daily_hours', 'completed_hours', 'observations', 'row_version'] as const
const errors = reactive(Object.fromEntries(errorKeys.map(key => [key, ''])) as Record<typeof errorKeys[number], string>)
const locked = computed(() => busy.value || actionEditing.value || isFetching.value || needsReload.value || !data.value?.can_update)
const planningDirty = computed(() => data.value && (completed.value !== data.value.completed_hours
  || Object.entries(plan).some(([field, value]) => value !== data.value?.[field as keyof WorkPlanning])))
const hourFields = ['estimated_hours', 'daily_hours', 'completed_hours'] as const
const contextFields = [{ key: 'assumptions', label: 'Premissas' }, { key: 'current_problems', label: 'Problemas atuais' },
  { key: 'expected_benefits', label: 'Ganhos esperados' }] as const
watch(data, item => {
  if (item) {
    Object.assign(plan, { difficulty: item.difficulty, priority: item.priority, estimated_hours: item.estimated_hours,
      daily_hours: item.daily_hours, completed_hours: item.completed_hours, observations: item.observations })
    completed.value = item.completed_hours
  }
}, { immediate: true })
watch(busy, value => emit('busy', value), { flush: 'sync' })

function close() { if (!busy.value) visible.value = false }
async function focusError() {
  await nextTick()
  form.value?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus()
}
async function reload() {
  if (busy.value) return
  reloading.value = true
  try {
    const result = await refetch()
    if (result.isSuccess) {
      await client.invalidateQueries({ queryKey: ['demands', 'work', 'tasks', props.id] })
      needsReload.value = false
      actionEditing.value = false
      reloadKey.value++
      serverError.value = ''
      errorKeys.forEach(key => { errors[key] = '' })
      feedback.value = 'Detalhes atualizados. Confira as informações antes de salvar novamente.'
      // A versão pode não mudar em uma falha anterior ao commit.
      if (result.data) {
        Object.assign(plan, { difficulty: result.data.difficulty, priority: result.data.priority,
          estimated_hours: result.data.estimated_hours, daily_hours: result.data.daily_hours,
          completed_hours: result.data.completed_hours, observations: result.data.observations })
        completed.value = result.data.completed_hours
      }
      emit('changed')
      await nextTick()
      document.getElementById(prefix + '-feedback')?.focus()
    }
  } finally { reloading.value = false }
}
async function save() {
  if (locked.value || !data.value) return
  errorKeys.forEach(key => { errors[key] = '' })
  feedback.value = ''
  serverError.value = ''
  if (completed.value === null) errors.completed_hours = 'Informe o tempo total realizado; use zero se ainda não houve execução.'
  if (errorKeys.some(key => errors[key]) || completed.value === null) { await focusError(); return }
  saving.value = true
  let saved = false
  try {
    const item = await workApi.plan(props.id, { ...plan, completed_hours: completed.value,
      observations: plan.observations?.trim() || null, row_version: data.value.row_version })
    client.setQueryData(queryKey, item)
    feedback.value = 'Planejamento e observações salvos.'
    saved = true
  } catch (error) {
    serverError.value = error instanceof Error ? error.message : 'Não foi possível salvar o planejamento.'
    if (error instanceof ApiError) {
      Object.assign(errors, validationMessages(error.detail, errorKeys))
      needsReload.value = [0, 401, 403, 409].includes(error.status) || error.status >= 500 || (error.status >= 200 && error.status < 300)
    } else needsReload.value = true
  } finally { saving.value = false }
  if (saved) {
    emit('changed')
    await nextTick()
    document.getElementById(prefix + '-feedback')?.focus()
  } else await focusError()
}
async function actionSaved(item: WorkDetail) {
  actionEditing.value = false
  client.setQueryData(queryKey, item)
  feedback.value = 'Ação registrada. A situação e o histórico foram atualizados.'
  emit('changed')
  await nextTick()
  document.getElementById(prefix + '-feedback')?.focus()
}
function contentSaved(item: WorkDetail) {
  const changed = data.value?.row_version !== item.row_version
  client.setQueryData(queryKey, item)
  feedback.value = changed ? 'Dados atualizados. A alteração ficou registrada no histórico.' : 'Os dados já estavam atualizados; nenhuma alteração foi necessária.'
  emit('changed')
}
async function contentClosed() {
  editingContent.value = false
  await nextTick()
  const target = document.getElementById(prefix + (needsReload.value ? '-reload' : '-edit')) ?? document.getElementById(prefix + '-feedback')
  target?.focus()
}
async function taskSaved(item: WorkDetail) {
  client.setQueryData(queryKey, item)
  emit('changed')
}
async function finalizeNotice() {
  if (actionSaving.value || needsReload.value || !data.value?.can_edit_content || data.value.kind !== 'aviso') return
  actionSaving.value = true
  serverError.value = ''
  try {
    const item = await workApi.finalizeNotice(props.id, data.value.row_version)
    client.setQueryData(queryKey, item)
    feedback.value = 'Aviso finalizado. Ele continua disponível no filtro de avisos finalizados.'
    noticeConfirm.value = false
    emit('changed')
  } catch (error) {
    serverError.value = error instanceof Error ? error.message : 'Não foi possível finalizar o aviso.'
    needsReload.value = !(error instanceof ApiError) || [0, 401, 403, 409].includes(error.status) || error.status >= 500 || (error.status >= 200 && error.status < 300)
  } finally { actionSaving.value = false }
}
async function noticeClosed() {
  await nextTick()
  const target = document.getElementById(prefix + (needsReload.value ? '-reload' : '-finalize')) ?? document.getElementById(prefix + '-feedback')
  target?.focus()
}
</script>

<template>
  <AppDialog :id="prefix" :visible="visible" :title="data ? workKind(data.kind).label + ' #' + id : 'Demanda #' + id"
    :subtitle="data?.kind === 'aviso' ? 'Informações e histórico do aviso' : 'Informações, tarefas e acompanhamento'" :icon="data ? workKind(data.kind).icon : 'pi pi-briefcase'"
    :busy="busy" @update:visible="close" @closed="emit('closed')">
    <RequestState :loading="isPending" :failed="isError" :error="error" :empty="false" loading-label="Carregando detalhes…"
      error-message="Não foi possível carregar a demanda ou aviso." not-found-message="Registro não encontrado para seu acesso." @retry="reload">
      <template v-if="data">
        <div class="flex flex-wrap gap-2">
          <Tag :value="workKind(data.kind).label" />
          <Tag v-if="data.kind !== 'aviso'" :value="statusLabel(data.status)" severity="secondary" />
          <Tag v-else :value="noticeStateLabel(data.notice_state)" severity="secondary" />
          <Tag v-if="data.is_overdue" value="Atrasada" severity="danger" icon="pi pi-clock" />
          <Tag v-if="data.source_request_id" :value="'Solicitação #' + data.source_request_id" severity="secondary" />
        </div>
        <h3 class="mt-4 break-words text-xl font-semibold text-dj-ink">{{ data.title }}</h3>
        <Message v-if="feedback" :id="prefix + '-feedback'" tabindex="-1" severity="success" role="status" class="mt-4">{{ feedback }}</Message>
        <p v-if="needsReload" role="status" class="mt-4 text-sm leading-6 text-dj-muted">Recarregue e confira os detalhes e o histórico antes de registrar outra alteração.</p>
        <nav aria-label="Detalhes da demanda" class="my-5 flex flex-wrap gap-2 rounded-xl border border-dj-border bg-dj-canvas p-2">
          <Button type="button" label="Informações" icon="pi pi-info-circle" :outlined="tab !== 'info'" :disabled="busy"
            :aria-current="tab === 'info' ? 'page' : undefined" :aria-controls="prefix + '-info'" @click="tab = 'info'" />
          <Button v-if="data.kind !== 'aviso'" type="button" label="Tarefas" icon="pi pi-check-square" :outlined="tab !== 'tasks'"
            :disabled="busy || Boolean(planningDirty) || actionEditing" :aria-current="tab === 'tasks' ? 'page' : undefined"
            :aria-controls="prefix + '-tasks'" @click="tab = 'tasks'" />
          <Button type="button" label="Histórico" icon="pi pi-history" :outlined="tab !== 'history'" :disabled="busy"
            :aria-current="tab === 'history' ? 'page' : undefined" :aria-controls="prefix + '-history'" @click="tab = 'history'" />
        </nav>
        <section v-show="tab === 'info'" :id="prefix + '-info'" aria-label="Informações da demanda">
          <dl class="grid gap-4 rounded-2xl border border-dj-border bg-dj-canvas p-4 text-sm sm:grid-cols-2">
            <div><dt class="text-xs text-dj-muted">Responsável</dt><dd class="mt-1">{{ data.responsible_name ?? 'Usuário indisponível' }}</dd></div>
            <div><dt class="text-xs text-dj-muted">Solicitante</dt><dd class="mt-1">{{ data.requester_name ?? 'Usuário indisponível' }}</dd></div>
            <div v-if="data.urgency"><dt class="text-xs text-dj-muted">Urgência</dt><dd class="mt-1">{{ data.urgency }}</dd></div>
            <div v-if="data.contributor_name"><dt class="text-xs text-dj-muted">Contribuinte</dt><dd class="mt-1">{{ data.contributor_name }}</dd></div>
            <div><dt class="text-xs text-dj-muted">Criada em</dt><dd class="mt-1">{{ displayDate(data.created_at) }}</dd></div>
            <div><dt class="text-xs text-dj-muted">Atualizada em</dt><dd class="mt-1">{{ displayDate(data.updated_at) }}</dd></div>
            <template v-if="data.kind === 'aviso'">
              <div><dt class="text-xs text-dj-muted">Data e hora de início</dt><dd class="mt-1">{{ data.starts_at ? displayDate(data.starts_at) : 'Não informado' }}</dd></div>
              <div><dt class="text-xs text-dj-muted">Data e hora de fim</dt><dd class="mt-1">{{ data.ends_at ? displayDate(data.ends_at) : 'Não informado' }}</dd></div>
              <div><dt class="text-xs text-dj-muted">Ocultar após o fim</dt><dd class="mt-1">{{ data.hide_after_end ? 'Sim' : 'Não' }}</dd></div>
              <div v-if="data.notice_finalized_at"><dt class="text-xs text-dj-muted">Finalizado em</dt><dd class="mt-1">{{ displayDate(data.notice_finalized_at) }}</dd></div>
            </template>
            <template v-else>
              <div v-if="data.scheduled_start_on"><dt class="text-xs text-dj-muted">Início agendado</dt><dd class="mt-1">{{ displayDay(data.scheduled_start_on) }}</dd></div>
              <div v-if="data.started_on"><dt class="text-xs text-dj-muted">Início realizado</dt><dd class="mt-1">{{ displayDay(data.started_on) }}</dd></div>
              <div><dt class="text-xs text-dj-muted">Prazo de entrega</dt><dd class="mt-1">{{ data.due_on ? displayDay(data.due_on) : 'Não definido' }}</dd></div>
              <div v-if="data.closed_at"><dt class="text-xs text-dj-muted">Encerramento</dt><dd class="mt-1">{{ displayDate(data.closed_at) }}</dd></div>
              <div v-if="data.expected_return_on"><dt class="text-xs text-dj-muted">Previsão de retorno</dt><dd class="mt-1">{{ displayDay(data.expected_return_on) }}</dd></div>
            </template>
          </dl>
          <p v-if="planningDirty && data.can_update" class="mt-4 text-sm text-dj-muted">Salve o planejamento antes de registrar uma ação, editar o conteúdo ou abrir as tarefas.</p>
          <DemandActions v-if="data.can_update" :key="data.row_version + ':' + reloadKey" :work="data"
            :disabled="busy || isFetching || isError || needsReload || Boolean(planningDirty)" @busy="actionSaving = $event"
            @editing="actionEditing = $event" @uncertain="needsReload = true" @saved="actionSaved" />
          <section class="mt-5">
            <h4 class="mb-2 text-sm font-semibold">{{ data.kind === 'erro' ? 'Descrição do erro' : ['projeto', 'melhoria'].includes(data.kind) ? 'Objetivo da demanda' : 'Descrição' }}</h4>
            <p class="whitespace-pre-wrap break-words text-sm leading-7 text-dj-muted">{{ data.description }}</p>
          </section>
          <template v-if="data.kind === 'projeto' || data.kind === 'melhoria'">
            <section v-for="field in contextFields" :key="field.key" class="mt-5">
              <h4 class="mb-2 text-sm font-semibold">{{ field.label }}</h4>
              <p class="whitespace-pre-wrap break-words text-sm leading-7 text-dj-muted">{{ data[field.key] ?? 'Não informado' }}</p>
            </section>
          </template>
          <section v-if="data.attachments.length" class="mt-5">
            <h4 class="mb-2 text-sm font-semibold">Documentos e evidências</h4>
            <ul class="space-y-2 text-sm">
              <li v-for="attachment in data.attachments" :key="attachment.id">
                <a :href="workApi.attachmentUrl(id, attachment.id)" class="inline-flex max-w-full items-center gap-2 rounded-lg px-2 py-2 text-dj-brand underline underline-offset-4">
                  <i class="pi pi-download shrink-0" aria-hidden="true" /><span class="min-w-0 break-words">{{ attachment.original_name }} ({{ fileSize(attachment.size_bytes) }})</span>
                </a>
              </li>
            </ul>
          </section>
          <form v-if="data.kind !== 'aviso'" :id="prefix + '-form'" ref="form" novalidate class="mt-6 border-t border-dj-border pt-5" @submit.prevent="save">
            <h4 class="mb-4 text-sm font-semibold">Planejamento e acompanhamento</h4>
            <p v-if="isFetching" role="status" class="mb-4 text-sm text-dj-muted">Atualizando informações…</p>
            <Message v-if="serverError" severity="error" role="alert" class="mb-4">{{ serverError }}</Message>
            <Message v-if="errors.row_version" severity="error" class="mb-4">{{ errors.row_version }}</Message>
            <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <FormField :id="prefix + '-difficulty'" label="Dificuldade" :error="errors.difficulty" v-slot="{ controlProps }">
                <Select v-model="plan.difficulty" :input-id="controlProps.id" :invalid="controlProps.invalid" :options="['Baixa', 'Média', 'Alta']"
                  :pt:label:aria-describedby="controlProps['aria-describedby']" show-clear :disabled="locked" placeholder="Não informada" class="w-full" />
              </FormField>
              <FormField :id="prefix + '-priority'" label="Prioridade (1 a 10)" :error="errors.priority" v-slot="{ controlProps }">
                <InputNumber v-model="plan.priority" :input-id="controlProps.id" :invalid="controlProps.invalid" :min="1" :max="10" :max-fraction-digits="0" :use-grouping="false"
                  :pt:pcInputText:root:aria-describedby="controlProps['aria-describedby']" :disabled="locked" placeholder="Não informada" class="w-full" pt:pcInputText:root:class="w-full" />
              </FormField>
              <FormField v-for="field in hourFields" :key="field" :id="prefix + '-' + field" :label="planningLabels[field] ?? field" :error="errors[field]" v-slot="{ controlProps }">
                <InputNumber v-if="field === 'completed_hours'" v-model="completed" :input-id="controlProps.id" :invalid="controlProps.invalid" :min="0" :max="99999.99"
                  :max-fraction-digits="2" locale="pt-BR" :pt:pcInputText:root:aria-describedby="controlProps['aria-describedby']" :disabled="locked" class="w-full" pt:pcInputText:root:class="w-full" />
                <InputNumber v-else v-model="plan[field]" :input-id="controlProps.id" :invalid="controlProps.invalid" :min="0" :max="99999.99"
                  :max-fraction-digits="2" locale="pt-BR" :pt:pcInputText:root:aria-describedby="controlProps['aria-describedby']" :disabled="locked" placeholder="Não informado" class="w-full" pt:pcInputText:root:class="w-full" />
              </FormField>
            </div>
            <p class="mt-2 text-xs leading-5 text-dj-muted">Prioridade 1 é a mais alta. Os tempos são informados em horas; o total realizado pode superar a estimativa.</p>
            <FormField :id="prefix + '-observations'" label="Observações" :error="errors.observations" class="mt-4" v-slot="{ controlProps }">
              <Textarea v-model="plan.observations" v-bind="controlProps" :rows="4" :maxlength="4000" :disabled="locked" class="w-full" />
            </FormField>
          </form>
        </section>
        <section v-if="tab === 'tasks' && data.kind !== 'aviso'" :id="prefix + '-tasks'" aria-label="Tarefas da demanda">
          <DemandTasks :key="id + ':' + reloadKey" :work="data" :disabled="needsReload || isFetching || Boolean(planningDirty)"
            @saved="taskSaved" @busy="taskBusy = $event" @uncertain="needsReload = true" />
        </section>
        <section v-show="tab === 'history'" :id="prefix + '-history'" aria-label="Histórico da demanda">
          <ol class="space-y-4 text-sm">
            <li v-for="event in data.history" :key="event.id" class="border-l-2 border-dj-border pl-3">
              <p class="font-medium">{{ workHistoryLabel(event.event_type) }}</p>
              <p v-if="event.fields.length" class="mt-1 text-dj-muted">Campos: {{ event.fields.map(field => workFieldLabels[field] ?? field).join(', ') }}.</p>
              <p v-for="change in event.transitions" :key="change.field" class="mt-1 whitespace-pre-wrap break-words text-xs leading-5 text-dj-muted">
                {{ workFieldLabels[change.field] ?? change.field }}: {{ workHistoryValue(change.field, change.before) }} → {{ workHistoryValue(change.field, change.after) }}
              </p>
              <p v-if="event.message" class="mt-2 whitespace-pre-wrap break-words leading-6">{{ event.message }}</p>
              <p class="mt-1 text-xs text-dj-muted">{{ event.event_type === 'auto_started' ? 'Sistema' : event.actor_name ?? 'Usuário indisponível' }} · {{ displayDate(event.created_at) }}</p>
            </li>
          </ol>
          <p v-if="!data.history.length" class="text-sm text-dj-muted">Nenhum evento registrado.</p>
        </section>
      </template>
    </RequestState>
    <DemandCreateDialog v-if="editingContent && data" :work="data" @saved="contentSaved" @closed="contentClosed" @uncertain="needsReload = true" />
    <AppDialog :id="prefix + '-notice-confirm'" :visible="noticeConfirm" title="Finalizar aviso" icon="pi pi-check" tone="neutral"
      :busy="actionSaving" :initial-focus-id="prefix + '-notice-cancel'" @update:visible="noticeConfirm = false" @closed="noticeClosed">
      <Message v-if="serverError" severity="error" role="alert" class="mb-4">{{ serverError }}</Message>
      <p class="break-words text-sm leading-6">Finalizar o aviso “{{ data?.title }}”? Ele sairá do mural padrão e continuará disponível para consulta nos avisos finalizados.</p>
      <p v-if="needsReload" class="mt-3 text-sm text-dj-muted">Feche esta confirmação e recarregue os detalhes antes de tentar novamente.</p>
      <template #footer>
        <Button type="button" label="Finalizar aviso" :loading="actionSaving" :disabled="actionSaving || needsReload" @click="finalizeNotice" />
        <SecondaryButton :id="prefix + '-notice-cancel'" type="button" label="Cancelar" outlined :disabled="actionSaving" @click="noticeConfirm = false" />
      </template>
    </AppDialog>
    <template #footer>
      <Button v-if="needsReload" :id="prefix + '-reload'" type="button" label="Recarregar detalhes" icon="pi pi-refresh" :loading="reloading" :disabled="busy" @click="reload" />
      <Button v-else-if="data?.can_update && !isError && tab === 'info' && !actionEditing" type="submit" :form="prefix + '-form'" label="Salvar planejamento" icon="pi pi-save" :loading="saving" :disabled="locked" />
      <Button v-if="data?.can_edit_content && !isError && tab === 'info' && !actionEditing" :id="prefix + '-edit'" type="button"
        label="Editar dados e responsável" icon="pi pi-pencil" outlined :disabled="busy || isFetching || needsReload || Boolean(planningDirty)" @click="editingContent = true" />
      <Button v-if="data?.kind === 'aviso' && data.can_edit_content && !isError && tab === 'info'" :id="prefix + '-finalize'" type="button"
        label="Finalizar aviso" icon="pi pi-check" outlined :disabled="busy || isFetching || needsReload" @click="serverError = ''; noticeConfirm = true" />
      <SecondaryButton type="button" label="Fechar" outlined :disabled="busy" @click="close" />
    </template>
  </AppDialog>
</template>
