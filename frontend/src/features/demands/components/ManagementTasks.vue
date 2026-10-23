<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import FormField from '@/shared/components/FormField.vue'
import Button from '@/volt/Button.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import Textarea from '@/volt/Textarea.vue'
import Select from '@/volt/Select.vue'
import InputNumber from '@/volt/InputNumber.vue'
import Checkbox from '@/volt/Checkbox.vue'
import Message from '@/volt/Message.vue'
import DemandDateField from './DemandDateField.vue'
import { managementApi } from '../managementApi'
import type { ManagedDetail, ManagementOptions, Task } from '../managementTypes'
import { dayLabel } from '../managementTypes'
const props = defineProps<{ demand: ManagedDetail; options: ManagementOptions }>()
const emit = defineEmits<{ saved: [value: ManagedDetail]; busy: [value: boolean] }>()
const busy = ref(false); const error = ref(''); const editing = ref(false); const taskId = ref<number | undefined>(); const taskVersion = ref(''); const removing = ref<number | null>(null)
const fields = reactive({ description: '', responsible_id: null as string | null, priority: null as number | null, deadline: null as string | null, observations: '', completed: false })
watch(busy, value => emit('busy', value), { flush: 'sync' })
function edit(task?: Task) {
  taskId.value = task?.id; taskVersion.value = task?.row_version ?? ''; editing.value = true
  Object.assign(fields, { description: task?.description ?? '', responsible_id: task?.responsible_id ?? null, priority: task?.priority ?? null,
    deadline: task?.deadline ?? null, observations: task?.observations ?? '', completed: !!task?.completed_at })
}
async function save(task?: Task, remove = false) {
  if (busy.value) return
  busy.value = true; error.value = ''
  try {
    const result = remove && task
      ? await managementApi.removeTask(props.demand.id, task.id, props.demand.row_version)
      : await managementApi.task(props.demand.id, task ? {
        description: task.description, responsible_id: task.responsible_id, priority: task.priority, deadline: task.deadline,
        observations: task.observations, completed: !task.completed_at, task_version: task.row_version, row_version: props.demand.row_version,
      } : { ...fields, row_version: props.demand.row_version, ...(taskId.value ? { task_version: taskVersion.value } : {}) }, task?.id ?? taskId.value)
    editing.value = false; removing.value = null; emit('saved', result)
  } catch (err) { error.value = err instanceof Error ? err.message : 'Não foi possível salvar a tarefa.' }
  finally { busy.value = false }
}
</script>
<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between gap-3"><h3 class="font-semibold">Tarefas · {{ demand.completed_tasks }}/{{ demand.total_tasks }}</h3>
      <Button v-if="demand.can_edit" type="button" label="Nova tarefa" icon="pi pi-plus" :disabled="busy || editing" @click="edit()" /></div>
    <form v-if="editing" class="space-y-4 rounded-xl border border-dj-border bg-dj-canvas p-4" @submit.prevent="save()">
      <FormField id="task-description" label="Descrição *"><Textarea id="task-description" v-model="fields.description" :rows="3" :maxlength="1000" :disabled="busy" class="w-full" required /></FormField>
      <div class="grid gap-4 sm:grid-cols-3">
        <FormField id="task-responsible" label="Responsável"><Select v-model="fields.responsible_id" input-id="task-responsible" :options="options.responsibles" option-label="name" option-value="id" show-clear :disabled="busy" class="w-full" /></FormField>
        <FormField id="task-priority" label="Prioridade"><InputNumber v-model="fields.priority" input-id="task-priority" :min="1" :max="10" :disabled="busy" fluid /></FormField>
        <DemandDateField id="task-deadline" v-model="fields.deadline" label="Prazo" :disabled="busy" />
      </div>
      <FormField id="task-observations" label="Observações"><Textarea id="task-observations" v-model="fields.observations" :rows="2" :maxlength="2000" :disabled="busy" class="w-full" /></FormField>
      <label class="flex items-center gap-2 text-sm"><Checkbox v-model="fields.completed" binary :disabled="busy" />Concluída</label>
      <div class="flex gap-2"><SecondaryButton type="button" label="Cancelar edição" outlined :disabled="busy" @click="editing = false" /><Button type="submit" label="Salvar tarefa" :loading="busy" :disabled="busy" /></div>
    </form>
    <Message v-if="error" severity="error" role="alert">{{ error }}</Message>
    <p v-if="!demand.tasks.length" class="text-sm text-dj-muted">Nenhuma tarefa cadastrada.</p>
    <article v-for="task in demand.tasks" :key="task.id" class="rounded-xl border border-dj-border p-4">
      <p class="whitespace-pre-wrap break-words text-sm" :class="{ 'line-through text-dj-muted': task.completed_at }">{{ task.description }}</p>
      <p class="mt-2 text-xs text-dj-muted">{{ task.responsible_name ?? 'Sem responsável' }} · Prazo: {{ dayLabel(task.deadline) }} · Prioridade: {{ task.priority ?? 'Não informada' }}</p>
      <p v-if="task.observations" class="mt-2 whitespace-pre-wrap text-sm text-dj-muted">{{ task.observations }}</p>
      <div v-if="demand.can_edit" class="mt-3 flex flex-wrap gap-2">
        <SecondaryButton type="button" :label="task.completed_at ? 'Reabrir' : 'Concluir'" :disabled="busy || editing" @click="save(task)" />
        <SecondaryButton type="button" label="Editar" :disabled="busy || editing" @click="edit(task)" />
        <SecondaryButton type="button" label="Remover" :disabled="busy || editing" @click="removing = task.id" />
      </div>
      <div v-if="removing === task.id" class="mt-3 flex flex-wrap items-center gap-2 text-sm" role="alert">
        Remover esta tarefa?<SecondaryButton type="button" label="Voltar" :disabled="busy" @click="removing = null" /><Button type="button" label="Confirmar remoção" :disabled="busy" @click="save(task, true)" />
      </div>
    </article>
  </div>
</template>
