<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { useMutation } from '@tanstack/vue-query'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
import AppDialog from '@/shared/components/AppDialog.vue'
import FormField from '@/shared/components/FormField.vue'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import Message from '@/volt/Message.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import { attendanceApi } from '../attendanceApi'
import type { AttendanceAction, AttendanceListDetail } from '../types'

const props = defineProps<{ eventId: number; list: AttendanceListDetail; action: AttendanceAction }>()
const emit = defineEmits<{ closed: [changed: boolean] }>()
const visible = ref(true)
const changed = ref(false)
const name = ref(props.list.name)
const nameError = ref('')
const submitError = ref('')
const renaming = computed(() => props.action.kind === 'rename')
const entry = computed(() => props.action.kind === 'delete-entry' ? props.action.entry : null)
const title = computed(() => renaming.value ? 'Editar nome da lista'
  : props.action.kind === 'delete-list' ? 'Excluir lista de presença' : 'Remover participante')
const allowed = computed(() => renaming.value ? props.list.capabilities.can_update
  : props.action.kind === 'delete-list' ? props.list.capabilities.can_delete : props.list.capabilities.can_delete_entry)
const { mutateAsync: save, isPending: saving } = useMutation({
  mutationFn: async (value: string) => {
    if (props.action.kind === 'rename') await attendanceApi.rename(props.eventId, props.list.id, value)
    else if (props.action.kind === 'delete-list') await attendanceApi.deleteList(props.eventId, props.list.id)
    else await attendanceApi.deleteEntry(props.eventId, props.list.id, props.action.entry.id)
  },
  retry: false,
})

async function focusInitial() {
  await nextTick()
  document.getElementById(renaming.value ? 'attendance-rename-name' : 'attendance-action-cancel')?.focus()
}

async function confirm() {
  if (saving.value || !allowed.value) return
  nameError.value = ''
  submitError.value = ''
  const value = name.value.trim()
  if (renaming.value && (!value || value.length > 120)) {
    nameError.value = 'Informe um nome entre 1 e 120 caracteres.'
    await focusInitial()
    return
  }
  try {
    await save(value)
  } catch (error) {
    if (renaming.value && error instanceof ApiError && error.status === 422) {
      nameError.value = validationMessages(error.detail, ['name'] as const).name
      await focusInitial()
    }
    submitError.value = error instanceof Error ? error.message : 'Não foi possível concluir a operação.'
    return
  }
  changed.value = true
  visible.value = false
}
</script>

<template>
  <AppDialog id="attendance-action-dialog" v-model:visible="visible" :title="title" :subtitle="list.name"
    :icon="renaming ? 'pi pi-pencil' : 'pi pi-trash'" :tone="renaming ? 'brand' : 'danger'" :busy="saving"
    description-id="attendance-action-help" :initial-focus-id="renaming ? 'attendance-rename-name' : 'attendance-action-cancel'"
    @closed="emit('closed', changed)">
    <form id="attendance-action-form" novalidate :aria-busy="saving" @submit.prevent="confirm">
      <p id="attendance-action-help" class="mb-5 text-sm leading-6 text-dj-muted">
        {{ renaming ? 'Altere o nome usado para identificar esta lista.'
          : entry ? 'Confira a pessoa antes de remover sua presença desta lista.'
          : 'Confira a lista antes de confirmar a exclusão.' }}
      </p>
      <FormField v-if="renaming" id="attendance-rename-name" v-slot="{ controlProps }" label="Nome da lista" :error="nameError">
        <InputText v-bind="controlProps" v-model="name" :maxlength="120" :disabled="saving" required autofocus
          pt:root:class="w-full rounded-xl" />
      </FormField>
      <template v-else>
        <div class="rounded-2xl border border-dj-border bg-dj-canvas p-5">
          <p class="break-words font-semibold text-dj-ink">{{ entry ? entry.name || 'Nome não informado' : list.name }}</p>
          <p v-if="entry" class="mt-2 text-sm text-dj-muted">
            Matrícula <span class="font-mono tabular-nums">{{ entry.registration.slice(-8) }}</span>
            · {{ entry.company || 'Empresa não informada' }}
          </p>
          <p v-else class="mt-2 text-sm text-dj-muted">{{ list.total }} {{ list.total === 1 ? 'presença registrada' : 'presenças registradas' }}</p>
        </div>
        <Message severity="warn" class="mt-5">
          {{ entry ? 'A presença desta pessoa será excluída somente desta lista. Esta ação não pode ser desfeita.'
            : 'A lista e todas as presenças registradas nela serão excluídas permanentemente. Esta ação não pode ser desfeita.' }}
        </Message>
      </template>
      <Message v-if="submitError" severity="error" class="mt-4">{{ submitError }}</Message>
    </form>
    <template #footer>
      <SecondaryButton id="attendance-action-cancel" type="button" label="Cancelar" outlined :disabled="saving" :autofocus="!renaming"
        pt:root:class="rounded-xl" @click="visible = false" />
      <Button type="submit" form="attendance-action-form" :label="saving ? 'Aguarde…' : renaming ? 'Salvar nome' : entry ? 'Remover participante' : 'Excluir lista'"
        :icon="renaming ? 'pi pi-check' : 'pi pi-trash'" :loading="saving" :disabled="saving || !allowed"
        pt:root:class="rounded-xl" :class="{ 'dj-danger-action': !renaming }" />
    </template>
  </AppDialog>
</template>
