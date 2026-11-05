<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
import AppDialog from '@/shared/components/AppDialog.vue'
import FormField from '@/shared/components/FormField.vue'
import RequestState from '@/shared/components/RequestState.vue'
import RecordOverview from '@/shared/components/RecordOverview.vue'
import Button from '@/volt/Button.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import Select from '@/volt/Select.vue'
import InputNumber from '@/volt/InputNumber.vue'
import InputText from '@/volt/InputText.vue'
import Textarea from '@/volt/Textarea.vue'
import Message from '@/volt/Message.vue'
import Tag from '@/volt/Tag.vue'
import Tabs from '@/volt/Tabs.vue'
import Tab from '@/volt/Tab.vue'
import TabList from '@/volt/TabList.vue'
import TabPanels from '@/volt/TabPanels.vue'
import TabPanel from '@/volt/TabPanel.vue'
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
const editingResponsible = ref(false)
const taskBusy = ref(false)
const noticeConfirm = ref(false)
const reloadKey = ref(0)
const busy = computed(() => saving.value || reloading.value || actionSaving.value || editingContent.value || taskBusy.value || noticeConfirm.value)
const needsReload = ref(false)
const tab = ref<string | number>('info')
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
  const target = document.getElementById(prefix + (needsReload.value ? '-reload' : editingResponsible.value ? '-owner-edit' : '-edit')) ?? document.getElementById(prefix + '-feedback')
  target?.focus()
  editingResponsible.value = false
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
    :subtitle="data?.kind === 'aviso' ? 'Informações e histórico do aviso' : 'Gerenciamento, informações e tarefas da demanda'" :icon="data ? workKind(data.kind).icon : 'pi pi-briefcase'"
    :busy="busy" @update:visible="close" @closed="emit('closed')">
    <RequestState :loading="isPending" :failed="isError" :error="error" :empty="false" loading-label="Carregando detalhes…"
      error-message="Não foi possível carregar a demanda ou aviso." not-found-message="Registro não encontrado para seu acesso." @retry="reload">
      <template v-if="data">
        <RecordOverview :title="data.title" :title-id="prefix + '-record-title'"
          :tone="data.status === 'concluido' ? 'success' : ['pausado', 'cancelado'].includes(data.status) || data.notice_finalized_at ? 'neutral' : 'brand'">
          <template #badges>
            <Tag :value="workKind(data.kind).label" />
            <Tag v-if="data.priority !== null" :value="'Prioridade ' + data.priority" severity="secondary" />
            <Tag v-if="data.kind !== 'aviso'" :value="statusLabel(data.status)" severity="secondary" />
            <Tag v-else :value="noticeStateLabel(data.notice_state)" severity="secondary" />
            <Tag v-if="data.difficulty" :value="'Dificuldade ' + data.difficulty" severity="secondary" />
            <Tag v-if="data.is_overdue" value="Atrasada" severity="danger" icon="pi pi-clock" />
            <Tag v-if="data.source_request_id" :value="'Solicitação #' + data.source_request_id" severity="secondary" />
          </template>
        </RecordOverview>
        <Message v-if="feedback" :id="prefix + '-feedback'" tabindex="-1" severity="success" role="status" class="mt-4">{{ feedback }}</Message>
        <p v-if="needsReload" role="status" class="mt-4 text-sm leading-6 text-dj-muted">Recarregue e confira os detalhes e o histórico antes de registrar outra alteração.</p>
        <Tabs v-model:value="tab" class="dj-dialog-tabs" scrollable :lazy="false">
          <TabList aria-label="Detalhes da demanda">
            <Tab value="info" :disabled="busy">Informações</Tab>
            <Tab v-if="data.kind !== 'aviso'" value="tasks" :disabled="busy || Boolean(planningDirty) || actionEditing">Tarefas</Tab>
            <Tab value="history" :disabled="busy">Histórico</Tab>
          </TabList>
          <TabPanels pt:root:class="dj-tab-panels">
            <TabPanel value="info">
              <div class="demand-detail-columns">
                <section class="dj-detail-panel" :aria-labelledby="prefix + '-management-title'">
                  <h4 :id="prefix + '-management-title'" class="dj-panel-heading border-b border-dj-border pb-3"><i class="pi pi-sliders-h" aria-hidden="true" />Gerenciamento</h4>
                  <form v-if="data.kind !== 'aviso'" :id="prefix + '-form'" ref="form" novalidate @submit.prevent="save">
                    <p v-if="isFetching" role="status" class="mb-3 text-sm text-dj-muted">Atualizando informações…</p>
                    <Message v-if="serverError" severity="error" role="alert" class="mb-3">{{ serverError }}</Message>
                    <Message v-if="errors.row_version" severity="error" class="mb-3">{{ errors.row_version }}</Message>
                    <div class="grid gap-3 sm:grid-cols-6">
                      <FormField :id="prefix + '-responsible'" label="Responsável" class="min-w-0 sm:col-span-2" v-slot="{ controlProps }">
                        <div class="flex min-w-0 gap-2">
                          <InputText :model-value="data.responsible_name ?? 'Usuário indisponível'" v-bind="controlProps" readonly
                            :title="data.responsible_name ?? 'Usuário indisponível'" class="min-w-0 w-full" />
                          <Button v-if="data.can_edit_content" :id="prefix + '-owner-edit'" type="button" icon="pi pi-pencil" outlined aria-label="Trocar responsável" title="Trocar responsável"
                            :disabled="busy || actionEditing || isFetching || needsReload || Boolean(planningDirty)" @click="editingResponsible = true; editingContent = true" />
                        </div>
                      </FormField>
                      <FormField :id="prefix + '-difficulty'" label="Dificuldade" :error="errors.difficulty" class="min-w-0 sm:col-span-2" v-slot="{ controlProps }">
                        <Select v-model="plan.difficulty" :input-id="controlProps.id" :invalid="controlProps.invalid" :options="['Baixa', 'Média', 'Alta']"
                          :pt:label:aria-describedby="controlProps['aria-describedby']" show-clear :disabled="locked" placeholder="Não informada" class="w-full" />
                      </FormField>
                      <FormField :id="prefix + '-priority'" label="Prioridade (1 a 10)" :error="errors.priority" class="min-w-0 sm:col-span-2" v-slot="{ controlProps }">
                        <InputNumber v-model="plan.priority" :input-id="controlProps.id" :invalid="controlProps.invalid" :min="1" :max="10" :max-fraction-digits="0" :use-grouping="false"
                          :pt:pcInputText:root:aria-describedby="controlProps['aria-describedby']" :disabled="locked" placeholder="Não informada" class="w-full" pt:pcInputText:root:class="w-full" />
                      </FormField>
                      <FormField :id="prefix + '-deadline'" label="Prazo de entrega" class="min-w-0 sm:col-span-3" v-slot="{ controlProps }">
                        <InputText :model-value="data.due_on ?? ''" v-bind="controlProps" type="date" readonly class="w-full" />
                      </FormField>
                      <FormField :id="prefix + '-started'" label="Data de início" class="min-w-0 sm:col-span-3" v-slot="{ controlProps }">
                        <InputText :model-value="data.started_on ?? ''" v-bind="controlProps" type="date" readonly class="w-full" />
                      </FormField>
                      <FormField v-for="field in hourFields" :key="field" :id="prefix + '-' + field" :label="field === 'completed_hours' ? 'Total realizado (h)' : planningLabels[field] ?? field" :error="errors[field]"
                        class="min-w-0 sm:col-span-2" v-slot="{ controlProps }">
                        <InputNumber v-if="field === 'completed_hours'" v-model="completed" :input-id="controlProps.id" :invalid="controlProps.invalid" :min="0" :max="99999.99"
                          :max-fraction-digits="2" locale="pt-BR" :pt:pcInputText:root:aria-describedby="controlProps['aria-describedby']" :disabled="locked" class="w-full" pt:pcInputText:root:class="w-full" />
                        <InputNumber v-else v-model="plan[field]" :input-id="controlProps.id" :invalid="controlProps.invalid" :min="0" :max="99999.99"
                          :max-fraction-digits="2" locale="pt-BR" :pt:pcInputText:root:aria-describedby="controlProps['aria-describedby']" :disabled="locked" placeholder="Não informado" class="w-full" pt:pcInputText:root:class="w-full" />
                      </FormField>
                      <FormField :id="prefix + '-observations'" label="Observações" :error="errors.observations" class="sm:col-span-6" v-slot="{ controlProps }">
                        <Textarea v-model="plan.observations" v-bind="controlProps" :rows="3" :maxlength="4000" :disabled="locked" class="w-full" />
                      </FormField>
                    </div>
                    <p class="mt-2 text-xs leading-5 text-dj-muted">Prioridade 1 é a mais alta. Os tempos são informados em horas.</p>
                  </form>
                  <dl v-else class="grid gap-3 text-sm sm:grid-cols-2">
                    <div class="sm:col-span-2"><dt class="text-xs text-dj-muted">Responsável</dt><dd class="mt-1 break-words">{{ data.responsible_name ?? 'Usuário indisponível' }}</dd></div>
                    <div><dt class="text-xs text-dj-muted">Início do aviso</dt><dd class="mt-1">{{ data.starts_at ? displayDate(data.starts_at) : 'Não informado' }}</dd></div>
                    <div><dt class="text-xs text-dj-muted">Fim do aviso</dt><dd class="mt-1">{{ data.ends_at ? displayDate(data.ends_at) : 'Não informado' }}</dd></div>
                    <div><dt class="text-xs text-dj-muted">Ocultar após o fim</dt><dd class="mt-1">{{ data.hide_after_end ? 'Sim' : 'Não' }}</dd></div>
                    <div v-if="data.notice_finalized_at"><dt class="text-xs text-dj-muted">Finalizado em</dt><dd class="mt-1">{{ displayDate(data.notice_finalized_at) }}</dd></div>
                  </dl>
                  <dl v-if="data.scheduled_start_on || data.expected_return_on || data.closed_at" class="mt-4 grid gap-3 rounded-lg bg-dj-canvas p-3 text-sm sm:grid-cols-2">
                    <div v-if="data.scheduled_start_on"><dt class="text-xs text-dj-muted">Início agendado</dt><dd class="mt-1">{{ displayDay(data.scheduled_start_on) }}</dd></div>
                    <div v-if="data.expected_return_on"><dt class="text-xs text-dj-muted">Previsão de retorno</dt><dd class="mt-1">{{ displayDay(data.expected_return_on) }}</dd></div>
                    <div v-if="data.closed_at"><dt class="text-xs text-dj-muted">Encerramento</dt><dd class="mt-1">{{ displayDate(data.closed_at) }}</dd></div>
                  </dl>
                  <p v-if="planningDirty && data.can_update" class="mt-3 text-xs leading-5 text-dj-muted">Salve o planejamento antes de registrar uma ação, editar o conteúdo ou abrir as tarefas.</p>
                  <DemandActions v-if="data.can_update" :key="data.row_version + ':' + reloadKey" :work="data" class="mt-4 border-t border-dj-border pt-4"
                    :disabled="busy || isFetching || isError || needsReload || Boolean(planningDirty)" @busy="actionSaving = $event"
                    @editing="actionEditing = $event" @uncertain="needsReload = true" @saved="actionSaved" />
                </section>
                <section class="dj-detail-panel" :aria-labelledby="prefix + '-data-title'">
                  <h4 :id="prefix + '-data-title'" class="dj-panel-heading border-b border-dj-border pb-3"><i class="pi pi-file" aria-hidden="true" />{{ data.kind === 'aviso' ? 'Dados do aviso' : data.source_request_id ? 'Dados da demanda recebida' : 'Dados da demanda interna' }}</h4>
                  <p v-if="data.source_request_id" class="mb-4 text-xs leading-5 text-dj-muted">Origem: solicitação #{{ data.source_request_id }}. Editar este trabalho preserva os dados enviados na solicitação original.</p>
                  <dl class="grid gap-3 text-sm sm:grid-cols-2">
                    <div class="border-b border-dj-border pb-3 sm:col-span-2"><dt class="text-xs text-dj-muted">Título</dt><dd class="mt-1 break-words font-semibold">{{ data.title }}</dd></div>
                    <div class="border-b border-dj-border pb-3 sm:col-span-2"><dt class="text-xs text-dj-muted">{{ data.kind === 'erro' ? 'Descrição do erro' : ['projeto', 'melhoria'].includes(data.kind) ? 'Descrição inicial / objetivo' : 'Descrição' }}</dt><dd class="mt-1 whitespace-pre-wrap break-words leading-6">{{ data.description }}</dd></div>
                    <template v-if="data.kind === 'projeto' || data.kind === 'melhoria'">
                      <div v-for="field in contextFields" :key="field.key" class="border-b border-dj-border pb-3 sm:col-span-2"><dt class="text-xs text-dj-muted">{{ field.label }}</dt><dd class="mt-1 whitespace-pre-wrap break-words leading-6">{{ data[field.key] ?? 'Não informado' }}</dd></div>
                    </template>
                    <div><dt class="text-xs text-dj-muted">Solicitante</dt><dd class="mt-1 break-words">{{ data.requester_name ?? 'Usuário indisponível' }}</dd></div>
                    <div><dt class="text-xs text-dj-muted">Contribuinte</dt><dd class="mt-1 break-words">{{ data.contributor_name ?? 'Sem contribuinte' }}</dd></div>
                    <div><dt class="text-xs text-dj-muted">Tipo</dt><dd class="mt-1">{{ workKind(data.kind).label }}</dd></div>
                    <div v-if="data.urgency"><dt class="text-xs text-dj-muted">Urgência</dt><dd class="mt-1">{{ data.urgency }}</dd></div>
                    <div v-if="data.source_request_id"><dt class="text-xs text-dj-muted">Solicitação de origem</dt><dd class="mt-1">#{{ data.source_request_id }}</dd></div>
                    <div><dt class="text-xs text-dj-muted">Criada em</dt><dd class="mt-1">{{ displayDate(data.created_at) }}</dd></div>
                    <div><dt class="text-xs text-dj-muted">Atualizada em</dt><dd class="mt-1">{{ displayDate(data.updated_at) }}</dd></div>
                  </dl>
                  <section class="mt-4 border-t border-dj-border pt-4" :aria-labelledby="prefix + '-documents-title'">
                    <h5 :id="prefix + '-documents-title'" class="mb-2 text-xs font-semibold text-dj-muted">Documentos e evidências</h5>
                    <ul class="space-y-2 text-sm">
                      <li v-for="attachment in data.attachments" :key="attachment.id">
                        <a :href="workApi.attachmentUrl(id, attachment.id)" class="inline-flex max-w-full items-center gap-2 rounded-lg px-2 py-2 text-dj-brand underline underline-offset-4">
                          <i class="pi pi-download shrink-0" aria-hidden="true" /><span class="min-w-0 break-words">{{ attachment.original_name }} ({{ fileSize(attachment.size_bytes) }})</span>
                        </a>
                      </li>
                    </ul>
                    <p v-if="!data.attachments.length" class="text-sm text-dj-muted">Nenhum documento disponível.</p>
                  </section>
                </section>
              </div>
            </TabPanel>
            <TabPanel v-if="data.kind !== 'aviso'" value="tasks">
              <DemandTasks v-if="tab === 'tasks'" :key="id + ':' + reloadKey" :work="data" :disabled="needsReload || isFetching || Boolean(planningDirty)"
                @saved="taskSaved" @busy="taskBusy = $event" @uncertain="needsReload = true" />
            </TabPanel>
            <TabPanel value="history">
              <ol class="space-y-3 text-sm">
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
            </TabPanel>
          </TabPanels>
        </Tabs>
      </template>
    </RequestState>
    <DemandCreateDialog v-if="editingContent && data" :work="data" :initial-field="editingResponsible ? 'responsible' : 'title'" @saved="contentSaved" @closed="contentClosed" @uncertain="needsReload = true" />
    <AppDialog :id="prefix + '-notice-confirm'" :visible="noticeConfirm" title="Finalizar aviso" icon="pi pi-check" tone="neutral" size="small"
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
        label="Editar dados e responsável" icon="pi pi-pencil" outlined :disabled="busy || isFetching || needsReload || Boolean(planningDirty)" @click="editingResponsible = false; editingContent = true" />
      <Button v-if="data?.kind === 'aviso' && data.can_edit_content && !isError && tab === 'info'" :id="prefix + '-finalize'" type="button"
        label="Finalizar aviso" icon="pi pi-check" outlined :disabled="busy || isFetching || needsReload" @click="serverError = ''; noticeConfirm = true" />
      <SecondaryButton type="button" label="Fechar" outlined :disabled="busy" @click="close" />
    </template>
  </AppDialog>
</template>

<style scoped>
.demand-detail-columns {
  display: grid;
  align-items: start;
  gap: 1rem;
}

@media (min-width: 74rem) {
  .demand-detail-columns {
    grid-template-columns: minmax(0, 1.08fr) minmax(0, 0.92fr);
  }
}
</style>
