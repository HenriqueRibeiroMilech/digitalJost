<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
import { usePagination } from '@/shared/composables/usePagination'
import AppDialog from '@/shared/components/AppDialog.vue'
import FormField from '@/shared/components/FormField.vue'
import ListHeader from '@/shared/components/ListHeader.vue'
import ListPagination from '@/shared/components/ListPagination.vue'
import RequestState from '@/shared/components/RequestState.vue'
import Button from '@/volt/Button.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import Checkbox from '@/volt/Checkbox.vue'
import InputText from '@/volt/InputText.vue'
import InputNumber from '@/volt/InputNumber.vue'
import Textarea from '@/volt/Textarea.vue'
import Select from '@/volt/Select.vue'
import Message from '@/volt/Message.vue'
import Tag from '@/volt/Tag.vue'
import { demandsApi, workApi } from '../api'
import { displayDate } from '../presentation'
import type { TaskFields, TaskItem, TaskSort, TaskStatus, WorkDetail } from '../types'

interface TaskDraft {
  id: string
  task: TaskItem | null
  fields: TaskFields
  original: TaskFields
  submissionKey: string
  errors: Partial<Record<typeof errorKeys[number], string>>
}

const props = defineProps<{ work: WorkDetail; disabled: boolean }>()
const emit = defineEmits<{ saved: [item: WorkDetail]; busy: [value: boolean]; uncertain: [] }>()
const client = useQueryClient()
const { page, perPage, resetPage } = usePagination()
const status = ref<TaskStatus>('all')
const sort = ref<TaskSort>('deadline')
const saving = ref<string | null>(null)
const deleting = ref<TaskDraft | null>(null)
const serverError = ref('')
const feedback = ref('')
const prefix = 'work-tasks-' + props.work.id
const errorKeys = ['title', 'description', 'responsible_id', 'priority', 'due_on', 'completed', 'row_version', 'task_row_version', 'submission_key'] as const
const drafts = reactive<Record<string, TaskDraft>>({})
const list = useQuery({ queryKey: ['demands', 'work', 'tasks', props.work.id, page, status, sort],
  queryFn: () => workApi.tasks(props.work.id, page.value, perPage, status.value, sort.value), retry: false,
  refetchOnWindowFocus: false, refetchOnReconnect: false })
const owners = useQuery({ queryKey: ['demands', 'management', 'responsibles'], queryFn: demandsApi.responsibles,
  enabled: computed(() => props.work.can_manage_tasks), retry: false, refetchOnWindowFocus: false, refetchOnReconnect: false })
const canManage = computed(() => props.work.can_manage_tasks && list.data.value?.capabilities.can_update === true)
const defaultOwner = computed(() => owners.data.value?.items.some(person => person.id === props.work.responsible_id) ? props.work.responsible_id : '')
const newDraft = ref(makeDraft(null))
const pendingCount = computed(() => Object.values(drafts).filter(isDirty).length + Number(isDirty(newDraft.value)))
const locked = computed(() => props.disabled || saving.value !== null || deleting.value !== null || list.isFetching.value || list.isError.value)
const navigationLocked = computed(() => locked.value || pendingCount.value > 0)
const rows = computed(() => {
  const items = (list.data.value?.items ?? []).map(task => drafts[String(task.id)]).filter((draft): draft is TaskDraft => Boolean(draft))
  const pending = Object.values(drafts).filter(draft => isDirty(draft) && !items.some(item => item.id === draft.id))
  return canManage.value ? [...items, ...pending, newDraft.value] : [...items, ...pending]
})
const busy = computed(() => saving.value !== null || deleting.value !== null || (pendingCount.value > 0 && !props.disabled))
const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit' })
  .formatToParts(new Date()).filter(part => ['year', 'month', 'day'].includes(part.type))
const todayDay = ['year', 'month', 'day'].map(type => today.find(part => part.type === type)?.value ?? '').join('-')

watch([status, sort], resetPage)
watch(busy, value => emit('busy', value), { flush: 'sync' })
onBeforeUnmount(() => emit('busy', false))
watch(list.error, error => { if (error) emit('uncertain') })
watch(() => list.isFetching.value, fetching => {
  if (!fetching && list.data.value && props.work.can_manage_tasks && !list.data.value.capabilities.can_update) emit('uncertain')
})
watch(defaultOwner, () => { if (!isDirty(newDraft.value)) newDraft.value = makeDraft(null) })
watch(list.data, result => {
  if (!result) return
  for (const task of result.items) {
    const id = String(task.id)
    const current = drafts[id]
    // Preservar também a versão original de outros rascunhos: não sobrescrever uma edição concorrente.
    if (!current || !isDirty(current)) drafts[id] = makeDraft(task)
  }
  for (const [id, draft] of Object.entries(drafts)) {
    if (!result.items.some(task => String(task.id) === id) && !isDirty(draft)) delete drafts[id]
  }
  if (!pendingCount.value) page.value = Math.min(page.value, Math.max(1, Math.ceil(result.total / perPage)))
}, { immediate: true })

function makeDraft(task: TaskItem | null): TaskDraft {
  const fields: TaskFields = task ? { title: task.title, description: task.description, responsible_id: task.responsible_id,
    priority: task.priority, due_on: task.due_on, completed: task.completed_at !== null }
    : { title: '', description: null, responsible_id: defaultOwner.value, priority: null, due_on: null, completed: false }
  return { id: task ? String(task.id) : 'new', task, fields, original: { ...fields }, submissionKey: task ? '' : crypto.randomUUID(), errors: {} }
}
function isDirty(draft: TaskDraft) {
  return (Object.keys(draft.original) as (keyof TaskFields)[]).some(field => draft.fields[field] !== draft.original[field])
}
function formId(draft: TaskDraft) { return prefix + '-' + draft.id }
function ownerOptions(draft: TaskDraft) {
  const items = owners.data.value?.items ?? []
  return draft.task && !items.some(person => person.id === draft.task?.responsible_id)
    ? [...items, { id: draft.task.responsible_id, name: draft.task.responsible_name ?? 'Responsável atual' }] : items
}
function isOverdue(draft: TaskDraft) { return !draft.fields.completed && draft.fields.due_on !== null && draft.fields.due_on < todayDay }
async function focusField(draft: TaskDraft) {
  await nextTick()
  const form = document.getElementById(formId(draft))
  const target = form?.querySelector<HTMLElement>('[aria-invalid="true"]') ?? document.getElementById(formId(draft) + '-title') ?? document.getElementById(prefix + '-root')
  target?.focus()
}
async function discard(draft: TaskDraft) {
  if (saving.value !== null || deleting.value) return
  if (draft.task) {
    const current = list.data.value?.items.find(task => task.id === draft.task?.id)
    drafts[draft.id] = makeDraft(current ?? draft.task)
  } else newDraft.value = makeDraft(null)
  await focusField(draft)
}
function failed(error: unknown, draft: TaskDraft) {
  serverError.value = error instanceof Error ? error.message : 'Não foi possível salvar a tarefa.'
  if (error instanceof ApiError) draft.errors = validationMessages(error.detail, errorKeys)
  if (!(error instanceof ApiError) || [0, 401, 403, 404, 409].includes(error.status) || error.status >= 500 || (error.status >= 200 && error.status < 300)) emit('uncertain')
}
async function focusFailure(draft: TaskDraft) {
  await nextTick()
  const invalid = document.getElementById(formId(draft))?.querySelector<HTMLElement>('[aria-invalid="true"]')
  const target = deleting.value ? document.getElementById(prefix + '-delete-error')
    : invalid && !invalid.matches(':disabled') ? invalid : document.getElementById(prefix + '-error')
  target?.focus()
}
async function saved(item: WorkDetail, message: string) {
  emit('saved', item)
  feedback.value = message
  await client.invalidateQueries({ queryKey: ['demands', 'work', 'tasks', props.work.id] })
}
async function submit(draft: TaskDraft) {
  if (locked.value || !canManage.value || owners.isPending.value || owners.isError.value || (draft.task && !isDirty(draft))) return
  draft.errors = {}
  serverError.value = ''
  if (!draft.fields.title.trim()) draft.errors.title = 'Descreva a tarefa.'
  if (!draft.fields.responsible_id) draft.errors.responsible_id = 'Selecione o responsável.'
  if (Object.keys(draft.errors).length) { await focusField(draft); return }
  const fields = { ...draft.fields, title: draft.fields.title.trim(), description: draft.fields.description?.trim() || null }
  saving.value = draft.id
  let committed = false
  try {
    const payload = { ...fields, row_version: props.work.row_version }
    const item = draft.task
      ? await workApi.updateTask(props.work.id, draft.task.id, { ...payload, task_row_version: draft.task.row_version })
      : await workApi.createTask(props.work.id, { ...payload, submission_key: draft.submissionKey })
    committed = true
    if (draft.task) { draft.fields = { ...fields }; draft.original = { ...fields } }
    else newDraft.value = makeDraft(null)
    await saved(item, draft.task ? 'Tarefa salva.' : 'Tarefa adicionada.')
  } catch (error) {
    if (committed) { serverError.value = 'A tarefa foi salva, mas não foi possível atualizar a lista. Recarregue os detalhes.'; emit('uncertain') }
    else failed(error, draft)
  } finally { saving.value = null }
  if (serverError.value) await focusFailure(draft)
  else if (committed) await focusField(draft.task ? draft : newDraft.value)
}
function confirmDelete(draft: TaskDraft) {
  if (locked.value || !canManage.value || !draft.task) return
  serverError.value = ''
  deleting.value = draft
}
async function remove() {
  const draft = deleting.value
  if (!draft?.task || saving.value !== null || props.disabled || !canManage.value) return
  saving.value = draft.id
  serverError.value = ''
  let committed = false
  try {
    const item = await workApi.deleteTask(props.work.id, draft.task.id, props.work.row_version, draft.task.row_version)
    committed = true
    delete drafts[draft.id]
    await saved(item, 'Tarefa excluída.')
    deleting.value = null
  } catch (error) {
    if (committed) { serverError.value = 'A tarefa foi excluída, mas não foi possível atualizar a lista. Recarregue os detalhes.'; emit('uncertain'); deleting.value = null }
    else failed(error, draft)
  } finally { saving.value = null }
  if (serverError.value) await focusFailure(draft)
}
const deleteOrigin = ref('')
watch(deleting, draft => { if (draft) deleteOrigin.value = formId(draft) + '-delete' })
async function restoreDeleteFocus() {
  await nextTick()
  const previous = document.getElementById(deleteOrigin.value)
  const target = previous && !previous.matches(':disabled') ? previous : document.getElementById(prefix + '-root')
  target?.focus()
}
function changePage(value: number) { if (!navigationLocked.value) page.value = value }
</script>

<template>
  <section :id="prefix + '-root'" tabindex="-1" :aria-labelledby="prefix + '-title'">
    <ListHeader :id="prefix + '-title'" title="Tarefas da demanda" :total="!list.isPending.value && !list.isError.value ? list.data.value?.total : undefined"
      description="Edite na própria lista e salve cada tarefa. O prazo de uma tarefa não altera o prazo da demanda." />
    <div class="mb-4 grid gap-3 sm:grid-cols-2">
      <div>
        <label :for="prefix + '-filter'" class="mb-2 block text-xs font-semibold text-dj-muted">Mostrar tarefas</label>
        <Select v-model="status" :input-id="prefix + '-filter'" :disabled="navigationLocked" class="w-full"
          :options="[{ value: 'all', label: 'Todas' }, { value: 'pending', label: 'Pendentes' }, { value: 'completed', label: 'Concluídas' }]" option-label="label" option-value="value" />
      </div>
      <div>
        <label :for="prefix + '-sort'" class="mb-2 block text-xs font-semibold text-dj-muted">Ordenar por</label>
        <Select v-model="sort" :input-id="prefix + '-sort'" :disabled="navigationLocked" class="w-full"
          :options="[{ value: 'deadline', label: 'Prazo mais próximo' }, { value: 'priority', label: 'Prioridade' }]" option-label="label" option-value="value" />
      </div>
    </div>
    <Message v-if="feedback" severity="success" role="status" class="mb-4">{{ feedback }}</Message>
    <Message v-if="pendingCount" severity="warn" role="status" class="mb-4">Há {{ pendingCount }} {{ pendingCount === 1 ? 'tarefa com alterações não salvas' : 'tarefas com alterações não salvas' }}.
      <template v-if="disabled">Recarregar os detalhes descarta estes rascunhos. Confira o resultado antes de editar novamente.</template>
      <template v-else>Salve ou desfaça as alterações para trocar de aba, filtro ou página.</template>
    </Message>
    <Message v-if="serverError && !deleting" :id="prefix + '-error'" severity="error" role="alert" tabindex="-1" class="mb-4">{{ serverError }}</Message>
    <Message v-if="owners.isError.value && work.can_manage_tasks" severity="error" class="mb-4">Não foi possível carregar os responsáveis.
      <SecondaryButton type="button" label="Tentar novamente" :disabled="saving !== null || Boolean(deleting)" @click="owners.refetch()" />
    </Message>
    <p v-if="!work.can_manage_tasks" class="mb-4 text-sm text-dj-muted">As tarefas ficam disponíveis para consulta. Para alterá-las, a demanda precisa estar aberta.</p>
    <RequestState :loading="list.isPending.value" :failed="list.isError.value" :error="list.error.value" :empty="false"
      loading-label="Carregando tarefas…" error-message="Não foi possível carregar as tarefas." @retry="list.refetch()">
      <p v-if="list.data.value?.total === 0" class="mb-4 text-sm text-dj-muted">Nenhuma tarefa para este filtro.</p>
      <div class="space-y-3">
        <form v-for="draft in rows" :id="formId(draft)" :key="draft.id" novalidate
          class="min-w-0 rounded-xl border border-dj-border border-l-4 bg-dj-surface p-4"
          :class="isDirty(draft) ? 'border-l-dj-brand bg-dj-canvas' : draft.fields.completed ? 'border-l-dj-success' : 'border-l-dj-border'"
          :aria-label="draft.task ? 'Tarefa #' + draft.task.id : 'Adicionar tarefa'" @submit.prevent="submit(draft)">
          <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
            <div class="flex flex-wrap items-center gap-3">
              <template v-if="draft.task">
                <div class="flex items-center gap-2">
                  <Checkbox v-model="draft.fields.completed" :input-id="formId(draft) + '-completed'" binary :disabled="!canManage || locked" />
                  <label :for="formId(draft) + '-completed'" class="text-sm font-medium">Concluída</label>
                </div>
                <span class="text-xs text-dj-muted">#{{ draft.task.id }}</span>
                <Tag :value="draft.fields.completed ? 'Concluída' : isOverdue(draft) ? 'Atrasada' : 'Pendente'"
                  :severity="draft.fields.completed ? 'success' : isOverdue(draft) ? 'danger' : 'secondary'" rounded />
              </template>
              <h4 v-else class="text-sm font-semibold">Nova tarefa</h4>
            </div>
            <Tag v-if="isDirty(draft)" value="Não salvo" severity="warn" rounded />
          </div>
          <div class="grid min-w-0 gap-3 sm:grid-cols-2 lg:grid-cols-12">
            <FormField :id="formId(draft) + '-title'" :label="draft.task ? 'Tarefa *' : 'Nova tarefa *'" :error="draft.errors.title" class="min-w-0 sm:col-span-2 lg:col-span-5" v-slot="{ controlProps }">
              <InputText v-if="!draft.task" v-model="draft.fields.title" v-bind="controlProps" required :maxlength="250" :disabled="locked" class="w-full"
                placeholder="Descreva uma entrega objetiva" />
              <Textarea v-else v-model="draft.fields.title" v-bind="controlProps" required :rows="2" :maxlength="250" :readonly="!canManage" :disabled="canManage && locked" class="w-full"
                placeholder="Descreva uma entrega objetiva" />
            </FormField>
            <FormField :id="formId(draft) + '-owner'" label="Responsável *" :error="draft.errors.responsible_id" class="min-w-0 lg:col-span-3" v-slot="{ controlProps }">
              <Select v-model="draft.fields.responsible_id" :input-id="controlProps.id" :invalid="controlProps.invalid" :options="ownerOptions(draft)" option-label="name" option-value="id" filter
                :pt:label:aria-describedby="controlProps['aria-describedby']" pt:label:aria-required="true" :loading="canManage && owners.isPending.value"
                :disabled="!canManage || locked || owners.isPending.value || owners.isError.value" class="w-full" />
            </FormField>
            <FormField :id="formId(draft) + '-priority'" label="Prioridade (opcional)" :error="draft.errors.priority" class="min-w-0 lg:col-span-2" v-slot="{ controlProps }">
              <InputNumber v-model="draft.fields.priority" :input-id="controlProps.id" :invalid="controlProps.invalid" :min="1" :max="10" :max-fraction-digits="0" :use-grouping="false"
                :pt:pcInputText:root:aria-describedby="controlProps['aria-describedby']" :disabled="!canManage || locked" placeholder="1 a 10" class="w-full" pt:pcInputText:root:class="w-full" />
            </FormField>
            <FormField :id="formId(draft) + '-due'" label="Prazo (opcional)" :error="draft.errors.due_on" class="min-w-0 lg:col-span-2" v-slot="{ controlProps }">
              <InputText :model-value="draft.fields.due_on ?? ''" v-bind="controlProps" type="date" max="9999-12-31" :readonly="!canManage" :disabled="canManage && locked" class="w-full"
                @update:model-value="draft.fields.due_on = $event || null" />
            </FormField>
            <FormField v-if="draft.task" :id="formId(draft) + '-description'" label="Observações (opcional)" :error="draft.errors.description" class="min-w-0 sm:col-span-2 lg:col-span-12" v-slot="{ controlProps }">
              <Textarea :model-value="draft.fields.description ?? ''" v-bind="controlProps" :rows="2" :maxlength="4000" :readonly="!canManage" :disabled="canManage && locked" class="w-full"
                @update:model-value="draft.fields.description = $event || null" />
            </FormField>
          </div>
          <p v-if="draft.task?.completed_at" class="mt-3 text-xs text-dj-muted">Concluída em {{ displayDate(draft.task.completed_at) }}</p>
          <Message v-if="draft.errors.row_version || draft.errors.task_row_version || draft.errors.submission_key || draft.errors.completed" severity="error" class="mt-3">
            {{ draft.errors.row_version || draft.errors.task_row_version || draft.errors.submission_key || draft.errors.completed }}
          </Message>
          <div v-if="canManage" class="mt-3 flex flex-wrap items-center gap-2">
            <Button type="submit" :label="draft.task ? 'Salvar' : 'Adicionar tarefa'" :icon="draft.task ? 'pi pi-save' : 'pi pi-plus'"
              :loading="saving === draft.id" :disabled="locked || owners.isPending.value || owners.isError.value || Boolean(draft.task && !isDirty(draft))" />
            <SecondaryButton v-if="draft.task" :id="formId(draft) + '-delete'" type="button" label="Excluir" icon="pi pi-trash" outlined class="text-dj-danger"
              :disabled="locked" @click="confirmDelete(draft)" />
            <SecondaryButton v-if="isDirty(draft) || Object.keys(draft.errors).length" type="button" :label="draft.task ? 'Desfazer alterações' : 'Limpar'" outlined
              :disabled="saving !== null || Boolean(deleting)" @click="discard(draft)" />
          </div>
        </form>
      </div>
    </RequestState>
    <fieldset :disabled="navigationLocked" class="min-w-0 border-0 p-0">
      <ListPagination v-if="list.data.value && !list.isError.value" :page="page" :per-page="perPage" :total="list.data.value.total" label="Páginas de tarefas" @update:page="changePage" />
    </fieldset>
    <AppDialog :id="prefix + '-delete-dialog'" :visible="Boolean(deleting)" title="Excluir tarefa" icon="pi pi-trash" tone="danger" :busy="saving !== null"
      :initial-focus-id="prefix + '-delete-cancel'" @update:visible="deleting = null" @closed="restoreDeleteFocus">
      <Message v-if="serverError" :id="prefix + '-delete-error'" severity="error" role="alert" tabindex="-1" class="mb-4">{{ serverError }}</Message>
      <p class="break-words text-sm leading-6">Excluir a tarefa “{{ deleting?.task?.title }}”? Somente esta tarefa será removida. A operação ficará registrada no histórico da demanda.</p>
      <p v-if="deleting && isDirty(deleting)" class="mt-3 text-sm text-dj-muted">As alterações não salvas desta tarefa também serão descartadas.</p>
      <p v-if="disabled" class="mt-3 text-sm text-dj-muted">Feche esta confirmação e recarregue os detalhes antes de tentar novamente.</p>
      <template #footer>
        <Button type="button" label="Excluir tarefa" class="dj-danger-action" :loading="saving !== null" :disabled="saving !== null || disabled" @click="remove" />
        <SecondaryButton :id="prefix + '-delete-cancel'" type="button" label="Cancelar" outlined :disabled="saving !== null" @click="deleting = null" />
      </template>
    </AppDialog>
  </section>
</template>
