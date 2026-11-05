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
import { demandsApi, workApi } from '../api'
import { displayDate, displayDay, fileSize, noticeStateLabel, planningLabels, requestStatus, workFieldLabels, workHistoryLabel, workHistoryValue, workKind } from '../presentation'
import type { WorkDetail, WorkPlanning } from '../types'
import DemandActions from './DemandActions.vue'
import DemandTasks from './DemandTasks.vue'

const props = defineProps<{ id: number }>()
const emit = defineEmits<{ closed: []; changed: []; busy: [value: boolean] }>()
const visible = ref(true)
const saving = ref(false)
const reloading = ref(false)
const actionSaving = ref(false)
const actionEditing = ref(false)
const taskBusy = ref(false)
const noticeConfirm = ref(false)
const reloadKey = ref(0)
const busy = computed(() => saving.value || reloading.value || actionSaving.value || taskBusy.value || noticeConfirm.value)
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
const status = computed(() => requestStatus(data.value?.status ?? ''))
const plan = reactive<WorkPlanning>({ difficulty: null, priority: null, estimated_hours: null, daily_hours: null, completed_hours: 0, observations: null })
const responsible = ref<string | null>(null)
const completed = ref<number | null>(0)
const errorKeys = ['responsible_id', 'difficulty', 'priority', 'estimated_hours', 'daily_hours', 'completed_hours', 'observations', 'row_version'] as const
const errors = reactive(Object.fromEntries(errorKeys.map(key => [key, ''])) as Record<typeof errorKeys[number], string>)
const locked = computed(() => busy.value || actionEditing.value || isFetching.value || needsReload.value || !(data.value?.can_update || data.value?.can_reassign))
const planningDirty = computed(() => data.value && (responsible.value !== data.value.responsible_id || completed.value !== data.value.completed_hours
  || Object.entries(plan).some(([field, value]) => value !== data.value?.[field as keyof WorkPlanning])))
const owners = useQuery({ queryKey: ['demands', 'management', 'responsibles'], queryFn: demandsApi.responsibles,
  enabled: computed(() => Boolean(data.value?.can_reassign)), retry: false, refetchOnWindowFocus: false, refetchOnReconnect: false })
const ownerOptions = computed(() => {
  const items = owners.data.value?.items ?? []
  const current = data.value
  return current && !items.some(person => person.id === current.responsible_id)
    ? [...items, { id: current.responsible_id, name: current.responsible_name ?? 'Responsável atual' }] : items
})
const hourFields = ['estimated_hours', 'daily_hours', 'completed_hours'] as const
const priorityOptions = Array.from({ length: 10 }, (_, index) => ({ label: String(index + 1), value: index + 1 }))
const contextFields = [{ key: 'assumptions', label: 'Premissas' }, { key: 'current_problems', label: 'Problemas atuais' },
  { key: 'expected_benefits', label: 'Ganhos esperados' }] as const
watch(data, item => {
  if (item) {
    Object.assign(plan, { difficulty: item.difficulty, priority: item.priority, estimated_hours: item.estimated_hours,
      daily_hours: item.daily_hours, completed_hours: item.completed_hours, observations: item.observations })
    completed.value = item.completed_hours
    responsible.value = item.responsible_id
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
        responsible.value = result.data.responsible_id
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
  if (!responsible.value) errors.responsible_id = 'Selecione o responsável.'
  if (completed.value === null) errors.completed_hours = 'Informe o tempo total realizado; use zero se ainda não houve execução.'
  if (errorKeys.some(key => errors[key]) || completed.value === null || !responsible.value) { await focusError(); return }
  saving.value = true
  let saved = false
  try {
    const item = data.value.kind === 'aviso'
      ? await workApi.assignResponsible(props.id, { responsible_id: responsible.value, row_version: data.value.row_version })
      : await workApi.plan(props.id, { ...plan, responsible_id: responsible.value, completed_hours: completed.value,
        observations: plan.observations?.trim() || null, row_version: data.value.row_version })
    client.setQueryData(queryKey, item)
    feedback.value = data.value.kind === 'aviso' ? 'Responsável salvo.' : 'Responsável, planejamento e observações salvos.'
    saved = true
  } catch (error) {
    serverError.value = error instanceof Error ? error.message : 'Não foi possível salvar as alterações.'
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
async function taskSaved(item: WorkDetail) {
  client.setQueryData(queryKey, item)
  emit('changed')
}
async function finalizeNotice() {
  if (actionSaving.value || needsReload.value || planningDirty.value || !data.value?.can_finalize_notice || data.value.kind !== 'aviso') return
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
          <Tag v-if="data.kind !== 'aviso'" :value="status.label" :icon="status.icon" severity="secondary" class="dj-tone-badge" :class="'dj-tone-' + status.tone" />
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
          <dl class="grid gap-3 sm:grid-cols-2">
            <div class="rounded-xl border border-primary-100 bg-primary-50/60 p-4">
              <dt class="flex items-center gap-2 text-xs font-semibold text-dj-muted"><i class="pi pi-calendar text-dj-brand" aria-hidden="true" />{{ data.kind === 'aviso' ? 'Início do aviso' : !data.started_on && data.scheduled_start_on ? 'Início agendado' : 'Data de início' }}</dt>
              <dd class="mt-2">
                <span class="text-lg font-semibold text-dj-ink">{{ data.kind === 'aviso' ? data.starts_at ? displayDate(data.starts_at) : 'Não informado' : data.started_on ? displayDay(data.started_on) : data.scheduled_start_on ? displayDay(data.scheduled_start_on) : 'Não iniciada' }}</span>
                <p v-if="data.expected_return_on" class="mt-1 text-xs text-dj-muted">Retorno previsto: {{ displayDay(data.expected_return_on) }}</p>
              </dd>
            </div>
            <div class="rounded-xl border p-4" :class="data.is_overdue ? 'border-dj-danger/20 bg-dj-danger-soft' : 'border-primary-100 bg-primary-50/60'">
              <dt class="flex items-center gap-2 text-xs font-semibold text-dj-muted"><i class="pi pi-clock" :class="data.is_overdue ? 'text-dj-danger' : 'text-dj-brand'" aria-hidden="true" />{{ data.kind === 'aviso' ? 'Fim do aviso' : 'Prazo de entrega' }}</dt>
              <dd class="mt-2">
                <span class="text-lg font-semibold" :class="data.is_overdue ? 'text-dj-danger' : 'text-dj-ink'">{{ data.kind === 'aviso' ? data.ends_at ? displayDate(data.ends_at) : 'Não informado' : data.due_on ? displayDay(data.due_on) : 'Não definido' }}</span>
                <p v-if="data.closed_at" class="mt-1 text-xs text-dj-muted">Encerramento: {{ displayDate(data.closed_at) }}</p>
              </dd>
            </div>
          </dl>
          <dl class="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt class="text-xs text-dj-muted">Solicitante</dt><dd class="mt-1 break-words">{{ data.requester_name ?? 'Usuário indisponível' }}
                <p v-if="data.contributor_name" class="mt-1 text-xs text-dj-muted">Contribuinte: {{ data.contributor_name }}</p>
              </dd>
            </div>
            <div><dt class="text-xs text-dj-muted">Urgência</dt><dd class="mt-1">{{ data.urgency ?? 'Não se aplica' }}</dd></div>
          </dl>
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
          <dl v-if="data.kind === 'aviso'" class="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-xs text-dj-muted">
            <div><dt class="inline">Ocultar após o fim: </dt><dd class="inline">{{ data.hide_after_end ? 'Sim' : 'Não' }}</dd></div>
            <div v-if="data.notice_finalized_at"><dt class="inline">Finalizado em: </dt><dd class="inline">{{ displayDate(data.notice_finalized_at) }}</dd></div>
          </dl>
          <p v-if="planningDirty && (data.can_update || data.can_reassign)" class="mt-4 text-sm text-dj-muted">{{ data.kind === 'aviso' ? 'Salve o responsável antes de finalizar o aviso.' : 'Salve o responsável e o planejamento antes de registrar uma ação ou abrir as tarefas.' }}</p>
          <DemandActions v-if="data.can_update" :key="data.row_version + ':' + reloadKey" :work="data"
            :disabled="busy || isFetching || isError || needsReload || Boolean(planningDirty)" @busy="actionSaving = $event"
            @editing="actionEditing = $event" @uncertain="needsReload = true" @saved="actionSaved" />
          <form :id="prefix + '-form'" ref="form" novalidate class="mt-6 border-t border-dj-border pt-5" @submit.prevent="save">
            <h4 class="mb-4 text-sm font-semibold">{{ data.kind === 'aviso' ? 'Responsável pelo aviso' : 'Planejamento e acompanhamento' }}</h4>
            <p v-if="isFetching" role="status" class="mb-4 text-sm text-dj-muted">Atualizando informações…</p>
            <Message v-if="serverError" severity="error" role="alert" class="mb-4">{{ serverError }}</Message>
            <Message v-if="errors.row_version" severity="error" class="mb-4">{{ errors.row_version }}</Message>
            <div class="grid gap-4" :class="data.kind !== 'aviso' ? 'sm:grid-cols-4' : undefined">
              <FormField :id="prefix + '-responsible'" label="Responsável" :error="errors.responsible_id" class="min-w-0" :class="data.kind !== 'aviso' ? 'sm:col-span-2' : undefined" v-slot="{ controlProps }">
                <Select v-model="responsible" :input-id="controlProps.id" :invalid="controlProps.invalid" :options="ownerOptions" option-label="name" option-value="id" filter
                  :loading="owners.isFetching.value" :disabled="locked || !data.can_reassign || owners.isPending.value || owners.isError.value"
                  :pt:label:aria-describedby="controlProps['aria-describedby']" pt:label:aria-required="true" placeholder="Selecione o responsável" class="w-full" />
              </FormField>
              <FormField v-if="data.kind !== 'aviso'" :id="prefix + '-difficulty'" label="Dificuldade" :error="errors.difficulty" class="min-w-0" v-slot="{ controlProps }">
                <Select v-model="plan.difficulty" :input-id="controlProps.id" :invalid="controlProps.invalid" :options="['Baixa', 'Média', 'Alta']"
                  :pt:label:aria-describedby="controlProps['aria-describedby']" show-clear :disabled="locked" placeholder="Não informada" class="w-full" />
              </FormField>
              <FormField v-if="data.kind !== 'aviso'" :id="prefix + '-priority'" label="Prioridade (1 a 10)" :error="errors.priority" class="min-w-0" v-slot="{ controlProps }">
                <Select v-model="plan.priority" :input-id="controlProps.id" :invalid="controlProps.invalid" :options="priorityOptions" option-label="label" option-value="value"
                  :pt:label:aria-describedby="controlProps['aria-describedby']" show-clear :disabled="locked" placeholder="Não definida" class="w-full" />
              </FormField>
            </div>
            <Message v-if="data.can_reassign && owners.isError.value" severity="error" class="mt-3">Não foi possível carregar os responsáveis.
              <SecondaryButton type="button" label="Tentar novamente" :disabled="locked || owners.isFetching.value" @click="owners.refetch()" />
            </Message>
            <p v-else-if="data.can_reassign && !owners.isPending.value && !owners.data.value?.items.length" class="mt-3 text-xs text-dj-muted">Nenhum responsável ativo disponível. O responsável atual pode ser mantido.</p>
            <template v-if="data.kind !== 'aviso'">
              <div class="mt-4 grid gap-4 sm:grid-cols-3">
                <FormField v-for="field in hourFields" :key="field" :id="prefix + '-' + field" :label="planningLabels[field] ?? field" :error="errors[field]" class="min-w-0" v-slot="{ controlProps }">
                  <InputNumber v-if="field === 'completed_hours'" v-model="completed" :input-id="controlProps.id" :invalid="controlProps.invalid" :min="0" :max="99999.99"
                    show-buttons button-layout="stacked" :step="1" :max-fraction-digits="2" locale="pt-BR"
                    :pt:incrementButton:aria-label="'Aumentar ' + (planningLabels[field] ?? field)" :pt:decrementButton:aria-label="'Diminuir ' + (planningLabels[field] ?? field)"
                    :pt:pcInputText:root:aria-describedby="controlProps['aria-describedby']" :disabled="locked" class="w-full" pt:pcInputText:root:class="min-w-0 w-full pr-12" />
                  <InputNumber v-else v-model="plan[field]" :input-id="controlProps.id" :invalid="controlProps.invalid" :min="0" :max="99999.99"
                    show-buttons button-layout="stacked" :step="1" :max-fraction-digits="2" locale="pt-BR"
                    :pt:incrementButton:aria-label="'Aumentar ' + (planningLabels[field] ?? field)" :pt:decrementButton:aria-label="'Diminuir ' + (planningLabels[field] ?? field)"
                    :pt:pcInputText:root:aria-describedby="controlProps['aria-describedby']" :disabled="locked" placeholder="Não informado" class="w-full" pt:pcInputText:root:class="min-w-0 w-full pr-12" />
                </FormField>
              </div>
              <p class="mt-2 text-xs leading-5 text-dj-muted">Prioridade 1 é a mais alta. Os tempos são informados em horas; o total realizado pode superar a estimativa.</p>
              <FormField :id="prefix + '-observations'" label="Observações" :error="errors.observations" class="mt-4" v-slot="{ controlProps }">
                <Textarea v-model="plan.observations" v-bind="controlProps" :rows="4" :maxlength="4000" :disabled="locked" class="w-full" />
              </FormField>
            </template>
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
      <Button v-else-if="(data?.can_update || data?.can_reassign) && !isError && tab === 'info' && !actionEditing" type="submit" :form="prefix + '-form'"
        :label="data?.kind === 'aviso' ? 'Salvar responsável' : 'Salvar planejamento'" icon="pi pi-save" :loading="saving" :disabled="locked" />
      <Button v-if="data?.can_finalize_notice && !isError && tab === 'info'" :id="prefix + '-finalize'" type="button"
        label="Finalizar aviso" icon="pi pi-check" outlined :disabled="busy || isFetching || needsReload || Boolean(planningDirty)" @click="serverError = ''; noticeConfirm = true" />
      <SecondaryButton type="button" label="Fechar" outlined :disabled="busy" @click="close" />
    </template>
  </AppDialog>
</template>
