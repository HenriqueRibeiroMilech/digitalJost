<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import AppDialog from '@/shared/components/AppDialog.vue'
import FormField from '@/shared/components/FormField.vue'
import Button from '@/volt/Button.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import InputText from '@/volt/InputText.vue'
import Textarea from '@/volt/Textarea.vue'
import Checkbox from '@/volt/Checkbox.vue'
import Message from '@/volt/Message.vue'
import DemandDateField from './DemandDateField.vue'
import { managementApi } from '../managementApi'
import type { Notice } from '../managementTypes'
import { localDateTimeLabel } from '../managementTypes'
const emit = defineEmits<{ saved: []; closed: []; busy: [value: boolean] }>()
const props = defineProps<{ notice: Notice }>()
const fields = reactive({ title: props.notice.title, description: props.notice.description, starts_at: props.notice.starts_at,
  ends_at: props.notice.ends_at, hide_after_end: props.notice.hide_after_end })
const busy = ref(false); const visible = ref(true); const editing = ref(false); const confirm = ref(false); const error = ref('')
watch(busy, value => emit('busy', value), { flush: 'sync' })
async function save(finish = false) {
  if (busy.value) return
  busy.value = true; error.value = ''
  try {
    if (finish) await managementApi.finishNotice(props.notice)
    else await managementApi.notice({ ...fields, row_version: props.notice.row_version }, props.notice.id)
    emit('saved'); visible.value = false
  } catch (err) { error.value = err instanceof Error ? err.message : 'Não foi possível atualizar o aviso.' }
  finally { busy.value = false }
}
</script>
<template>
  <AppDialog id="management-notice" :visible="visible" :title="notice.title" icon="pi pi-megaphone" :busy="busy" @update:visible="visible = false" @closed="emit('closed')">
    <form v-if="editing" id="notice-edit-form" class="space-y-4" @submit.prevent="save()">
      <FormField id="notice-edit-title" label="Título *"><InputText id="notice-edit-title" v-model="fields.title" :maxlength="250" :disabled="busy" required class="w-full" /></FormField>
      <FormField id="notice-edit-description" label="Descrição *"><Textarea id="notice-edit-description" v-model="fields.description" :maxlength="4000" :rows="4" :disabled="busy" required class="w-full" /></FormField>
      <div class="grid gap-4 sm:grid-cols-2"><DemandDateField id="notice-edit-start" v-model="fields.starts_at" time label="Início" :disabled="busy" /><DemandDateField id="notice-edit-end" v-model="fields.ends_at" time label="Fim" :disabled="busy" /></div>
      <label class="flex items-center gap-2"><Checkbox v-model="fields.hide_after_end" binary :disabled="busy" />Finalizar automaticamente após o fim</label>
    </form>
    <div v-else class="space-y-4">
      <p class="whitespace-pre-wrap break-words text-sm leading-7">{{ notice.description }}</p>
      <p class="text-sm text-dj-muted">Início: {{ localDateTimeLabel(notice.starts_at) }} · Fim: {{ localDateTimeLabel(notice.ends_at) }}</p>
      <p v-if="notice.hide_after_end" class="text-xs text-dj-muted">Finalização automática após o fim.</p>
    </div>
    <Message v-if="error" severity="error" class="mt-4">{{ error }}</Message>
    <div v-if="confirm" class="mt-5 flex flex-wrap items-center gap-2" role="alert">Finalizar este aviso?<SecondaryButton type="button" label="Voltar" :disabled="busy" @click="confirm = false" /><Button type="button" label="Confirmar" :disabled="busy" @click="save(true)" /></div>
    <template #footer>
      <SecondaryButton type="button" label="Fechar" outlined :disabled="busy" @click="visible = false" />
      <SecondaryButton v-if="notice.can_edit && !editing" type="button" label="Finalizar aviso" outlined :disabled="busy" @click="confirm = true" />
      <Button v-if="notice.can_edit && !editing" type="button" label="Editar" :disabled="busy" @click="editing = true" />
      <Button v-if="editing" type="submit" form="notice-edit-form" label="Salvar aviso" :loading="busy" :disabled="busy" />
    </template>
  </AppDialog>
</template>
