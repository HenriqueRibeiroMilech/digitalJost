<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
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
import InputText from '@/volt/InputText.vue'
import InputNumber from '@/volt/InputNumber.vue'
import Textarea from '@/volt/Textarea.vue'
import Select from '@/volt/Select.vue'
import Message from '@/volt/Message.vue'
import Tag from '@/volt/Tag.vue'
import { demandsApi, workApi } from '../api'
import { displayDate, displayDay } from '../presentation'
import type { TaskFields, TaskItem, TaskStatus, WorkDetail } from '../types'

const props = defineProps<{ work: WorkDetail; disabled: boolean }>()
const emit = defineEmits<{ saved: [item: WorkDetail]; busy: [value: boolean]; uncertain: [] }>()
const client = useQueryClient()
const { page, perPage, resetPage } = usePagination()
const status = ref<TaskStatus>('pending')
const dialog = ref(false)
const deleting = ref(false)
const saving = ref(false)
const selected = ref<TaskItem | null>(null)
const key = ref('')
const serverError = ref('')
const feedback = ref('')
const form = ref<HTMLFormElement | null>(null)
const prefix = 'work-tasks-' + props.work.id
const origin = ref(prefix + '-new')
const fields = reactive<TaskFields>({ title: '', description: null, responsible_id: '', priority: null, due_on: null, completed: false })
const errorKeys = ['title', 'description', 'responsible_id', 'priority', 'due_on', 'completed', 'row_version', 'task_row_version', 'submission_key'] as const
const errors = reactive(Object.fromEntries(errorKeys.map(field => [field, ''])) as Record<typeof errorKeys[number], string>)
const list = useQuery({ queryKey: ['demands', 'work', 'tasks', props.work.id, page, status],
  queryFn: () => workApi.tasks(props.work.id, page.value, perPage, status.value), retry: false,
  refetchOnWindowFocus: false, refetchOnReconnect: false })
const owners = useQuery({ queryKey: ['demands', 'management', 'responsibles'], queryFn: demandsApi.responsibles,
  enabled: computed(() => props.work.can_manage_tasks), retry: false, refetchOnWindowFocus: false })
const editable = computed(() => props.work.can_manage_tasks && !props.disabled && !list.isFetching.value && !list.isError.value)
const locked = computed(() => props.disabled || saving.value)
const ownerOptions = computed(() => {
  const items = owners.data.value?.items ?? []
  return selected.value && !items.some(person => person.id === selected.value?.responsible_id)
    ? [...items, { id: selected.value.responsible_id, name: selected.value.responsible_name ?? 'Responsável atual' }] : items
})
watch(status, resetPage)
watch(() => saving.value || dialog.value, value => emit('busy', value), { flush: 'sync' })
watch(list.data, result => { if (result) page.value = Math.min(page.value, Math.max(1, Math.ceil(result.total / perPage))) })

function open(task: TaskItem | null, remove = false) {
  if (!editable.value || saving.value) return
  selected.value = task
  deleting.value = remove
  key.value = crypto.randomUUID()
  origin.value = task ? prefix + (remove ? '-delete-' : '-edit-') + task.id : prefix + '-new'
  serverError.value = ''
  errorKeys.forEach(field => { errors[field] = '' })
  Object.assign(fields, task ? { title: task.title, description: task.description, responsible_id: task.responsible_id,
    priority: task.priority, due_on: task.due_on, completed: task.completed_at !== null }
    : { title: '', description: null, responsible_id: owners.data.value?.items.some(person => person.id === props.work.responsible_id) ? props.work.responsible_id : '', priority: null, due_on: null, completed: false })
  dialog.value = true
}
function close() { if (!saving.value) dialog.value = false }
async function restoreFocus() {
  await nextTick()
  const previous = document.getElementById(origin.value)
  const target = previous && !previous.matches(':disabled') ? previous : document.getElementById(prefix + '-root')
  target?.focus()
}
async function failed(error: unknown) {
  serverError.value = error instanceof Error ? error.message : 'Não foi possível salvar a tarefa.'
  if (error instanceof ApiError) Object.assign(errors, validationMessages(error.detail, errorKeys))
  if (!(error instanceof ApiError) || [0, 401, 403, 404, 409].includes(error.status) || error.status >= 500 || (error.status >= 200 && error.status < 300)) emit('uncertain')
  await nextTick()
  const target = form.value?.querySelector<HTMLElement>('[aria-invalid="true"]') ?? document.getElementById(prefix + (dialog.value ? '-dialog-error' : '-error'))
  target?.focus()
}
async function saved(item: WorkDetail, message: string) {
  emit('saved', item)
  feedback.value = message
  await client.invalidateQueries({ queryKey: ['demands', 'work', 'tasks', props.work.id] })
}
async function submit() {
  if (locked.value || !editable.value) return
  errorKeys.forEach(field => { errors[field] = '' })
  serverError.value = ''
  if (!deleting.value) {
    if (!fields.title.trim()) errors.title = 'Informe o título da tarefa.'
    if (!fields.responsible_id) errors.responsible_id = 'Selecione o responsável.'
  }
  if (errorKeys.some(field => errors[field])) { await nextTick(); form.value?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus(); return }
  saving.value = true
  try {
    const payload = { ...fields, title: fields.title.trim(), description: fields.description?.trim() || null, row_version: props.work.row_version }
    const item = deleting.value && selected.value
      ? await workApi.deleteTask(props.work.id, selected.value.id, props.work.row_version, selected.value.row_version)
      : selected.value ? await workApi.updateTask(props.work.id, selected.value.id, { ...payload, task_row_version: selected.value.row_version })
        : await workApi.createTask(props.work.id, { ...payload, submission_key: key.value })
    await saved(item, deleting.value ? 'Tarefa excluída.' : 'Tarefa salva.')
    dialog.value = false
  } catch (error) { await failed(error) }
  finally { saving.value = false }
}
async function toggle(task: TaskItem) {
  if (!editable.value || saving.value || dialog.value) return
  origin.value = prefix + '-toggle-' + task.id
  serverError.value = ''
  saving.value = true
  try {
    const item = await workApi.updateTask(props.work.id, task.id, { title: task.title, description: task.description,
      responsible_id: task.responsible_id, priority: task.priority, due_on: task.due_on, completed: task.completed_at === null,
      row_version: props.work.row_version, task_row_version: task.row_version })
    await saved(item, task.completed_at ? 'Tarefa reaberta.' : 'Tarefa concluída.')
    await restoreFocus()
  } catch (error) { await failed(error) }
  finally { saving.value = false }
}
</script>

<template>
  <section :id="prefix + '-root'" tabindex="-1" :aria-labelledby="prefix + '-title'">
    <div class="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <label :for="prefix + '-filter'" class="mb-2 block text-xs font-semibold text-dj-muted">Mostrar tarefas</label>
        <Select v-model="status" :input-id="prefix + '-filter'" :disabled="saving || dialog" :options="[{ value: 'pending', label: 'Pendentes' }, { value: 'completed', label: 'Concluídas' }, { value: 'all', label: 'Todas' }]" option-label="label" option-value="value" />
      </div>
      <Button v-if="work.can_manage_tasks" :id="prefix + '-new'" type="button" label="Nova tarefa" icon="pi pi-plus" :disabled="!editable || saving || dialog" @click="open(null)" />
    </div>
    <ListHeader :id="prefix + '-title'" title="Tarefas da demanda" :total="!list.isPending.value && !list.isError.value ? list.data.value?.total : undefined"
      description="Prioridade, prazo e conclusão de cada entrega, sem alterar o prazo da demanda." />
    <Message v-if="feedback" severity="success" role="status" class="mb-4">{{ feedback }}</Message>
    <Message v-if="serverError && !dialog" :id="prefix + '-error'" severity="error" role="alert" tabindex="-1" class="mb-4">{{ serverError }}</Message>
    <p v-if="!work.can_manage_tasks" class="mb-4 text-sm text-dj-muted">As tarefas ficam disponíveis para consulta. Para alterá-las, a demanda precisa estar aberta.</p>
    <RequestState :loading="list.isPending.value" :failed="list.isError.value" :error="list.error.value" :empty="list.data.value?.items.length === 0"
      loading-label="Carregando tarefas…" empty-title="Nenhuma tarefa para este filtro" empty-description="Altere o filtro ou cadastre uma tarefa para esta demanda."
      error-message="Não foi possível carregar as tarefas." @retry="list.refetch()">
      <div class="space-y-3">
        <article v-for="task in list.data.value?.items ?? []" :key="task.id" :aria-labelledby="prefix + '-task-' + task.id" class="rounded-2xl border border-dj-border bg-dj-surface p-4">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <h4 :id="prefix + '-task-' + task.id" class="min-w-0 break-words text-sm font-semibold">{{ task.title }}</h4>
            <Tag :value="task.completed_at ? 'Concluída' : 'Pendente'" :severity="task.completed_at ? 'success' : 'secondary'" rounded />
          </div>
          <p v-if="task.description" class="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-dj-muted">{{ task.description }}</p>
          <dl class="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs leading-5 text-dj-muted">
            <div><dt class="font-semibold">Responsável</dt><dd>{{ task.responsible_name ?? 'Usuário indisponível' }}</dd></div>
            <div><dt class="font-semibold">Prioridade</dt><dd>{{ task.priority ?? 'Não definida' }}</dd></div>
            <div><dt class="font-semibold">Prazo</dt><dd>{{ task.due_on ? displayDay(task.due_on) : 'Não definido' }}</dd></div>
            <div v-if="task.completed_at"><dt class="font-semibold">Concluída em</dt><dd>{{ displayDate(task.completed_at) }}</dd></div>
          </dl>
          <div v-if="work.can_manage_tasks" class="mt-4 flex flex-wrap gap-2 border-t border-dj-border pt-3">
            <Button :id="prefix + '-toggle-' + task.id" type="button" :label="task.completed_at ? 'Reabrir tarefa' : 'Concluir tarefa'" :icon="task.completed_at ? 'pi pi-replay' : 'pi pi-check'" :disabled="!editable || saving || dialog" @click="toggle(task)" />
            <Button :id="prefix + '-edit-' + task.id" type="button" label="Editar" icon="pi pi-pencil" outlined :disabled="!editable || saving || dialog" @click="open(task)" />
            <SecondaryButton :id="prefix + '-delete-' + task.id" type="button" label="Excluir" icon="pi pi-trash" outlined class="text-dj-danger" :disabled="!editable || saving || dialog" @click="open(task, true)" />
          </div>
        </article>
      </div>
    </RequestState>
    <ListPagination v-if="list.data.value && !list.isError.value" v-model:page="page" :per-page="perPage" :total="list.data.value.total" label="Páginas de tarefas" />
    <AppDialog :id="prefix + '-dialog'" :visible="dialog" :title="deleting ? 'Excluir tarefa' : selected ? 'Editar tarefa' : 'Nova tarefa'"
      :icon="deleting ? 'pi pi-trash' : 'pi pi-check-square'" :tone="deleting ? 'danger' : 'brand'" :busy="saving"
      :initial-focus-id="prefix + (deleting ? '-cancel' : '-name')" @update:visible="close" @closed="restoreFocus">
      <Message v-if="serverError" :id="prefix + '-dialog-error'" severity="error" role="alert" tabindex="-1" class="mb-4">{{ serverError }}</Message>
      <p v-if="disabled" class="mb-4 text-sm text-dj-muted">Feche esta janela e recarregue os detalhes da demanda antes de outra alteração.</p>
      <p v-if="deleting" class="break-words text-sm leading-6">Excluir a tarefa “{{ selected?.title }}”? Somente esta tarefa será removida. A operação ficará registrada no histórico da demanda.</p>
      <form v-else :id="prefix + '-form'" ref="form" novalidate class="space-y-4" @submit.prevent="submit">
        <FormField :id="prefix + '-name'" label="Título *" :error="errors.title" v-slot="{ controlProps }">
          <InputText v-model="fields.title" v-bind="controlProps" required :maxlength="250" :disabled="locked" class="w-full" />
        </FormField>
        <FormField :id="prefix + '-description'" label="Descrição e observações (opcional)" :error="errors.description" v-slot="{ controlProps }">
          <Textarea v-model="fields.description" v-bind="controlProps" :rows="4" :maxlength="4000" :disabled="locked" class="w-full" />
        </FormField>
        <FormField :id="prefix + '-owner'" label="Responsável *" :error="errors.responsible_id" v-slot="{ controlProps }">
          <Select v-model="fields.responsible_id" :input-id="controlProps.id" :invalid="controlProps.invalid" :options="ownerOptions" option-label="name" option-value="id" filter
            :pt:label:aria-describedby="controlProps['aria-describedby']" :loading="owners.isPending.value" :disabled="locked || owners.isPending.value || owners.isError.value" class="w-full" />
        </FormField>
        <Message v-if="owners.isError.value" severity="error">Não foi possível carregar os responsáveis.
          <SecondaryButton type="button" label="Tentar novamente" :disabled="saving" @click="owners.refetch()" />
        </Message>
        <div class="grid gap-4 sm:grid-cols-2">
          <FormField :id="prefix + '-priority'" label="Prioridade (1 a 10, opcional)" :error="errors.priority" v-slot="{ controlProps }">
            <InputNumber v-model="fields.priority" :input-id="controlProps.id" :invalid="controlProps.invalid" :min="1" :max="10" :max-fraction-digits="0" :use-grouping="false"
              :pt:pcInputText:root:aria-describedby="controlProps['aria-describedby']" :disabled="locked" class="w-full" pt:pcInputText:root:class="w-full" />
          </FormField>
          <FormField :id="prefix + '-due'" label="Prazo (opcional)" :error="errors.due_on" v-slot="{ controlProps }">
            <InputText :model-value="fields.due_on ?? ''" v-bind="controlProps" type="date" max="9999-12-31" :disabled="locked" class="w-full" @update:model-value="fields.due_on = $event || null" />
          </FormField>
        </div>
        <label class="flex items-center gap-2 text-sm"><input v-model="fields.completed" type="checkbox" :disabled="locked" class="size-4 accent-dj-brand" /> Tarefa concluída</label>
      </form>
      <template #footer>
        <Button :type="deleting ? 'button' : 'submit'" :form="deleting ? undefined : prefix + '-form'" :label="deleting ? 'Excluir tarefa' : 'Salvar tarefa'"
          :class="{ 'dj-danger-action': deleting }" :loading="saving" :disabled="locked || !editable || (!deleting && (owners.isPending.value || owners.isError.value))" @click="deleting && submit()" />
        <SecondaryButton :id="prefix + '-cancel'" type="button" label="Cancelar" outlined :disabled="saving" @click="close" />
      </template>
    </AppDialog>
  </section>
</template>
