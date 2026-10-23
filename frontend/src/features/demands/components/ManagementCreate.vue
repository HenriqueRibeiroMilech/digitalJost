<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import AppDialog from '@/shared/components/AppDialog.vue'
import FormField from '@/shared/components/FormField.vue'
import Button from '@/volt/Button.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import Select from '@/volt/Select.vue'
import InputText from '@/volt/InputText.vue'
import Textarea from '@/volt/Textarea.vue'
import Checkbox from '@/volt/Checkbox.vue'
import Message from '@/volt/Message.vue'
import ManagementEditor from './ManagementEditor.vue'
import DemandDateField from './DemandDateField.vue'
import { managementApi } from '../managementApi'
import { blankManagementFields, demandTypes } from '../managementTypes'
import type { DemandType, ManagementOptions } from '../managementTypes'
import { fileAccept } from '../presentation'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
const props = defineProps<{ options: ManagementOptions }>()
const emit = defineEmits<{ saved: []; closed: []; busy: [value: boolean] }>()
const kind = ref<DemandType | 'aviso' | null>(null)
const fields = ref(blankManagementFields(props.options.current_user_id))
const notice = reactive({ title: '', description: '', starts_at: null as string | null, ends_at: null as string | null, hide_after_end: false })
const files = ref<File[]>([]); const contributor = ref<string | null>(null); const key = crypto.randomUUID()
const busy = ref(false); const visible = ref(true); const error = ref(''); const uncertain = ref(false)
const errors = ref<Record<string, string>>({})
watch(busy, value => emit('busy', value), { flush: 'sync' })
async function submit() {
  if (busy.value || !kind.value) return
  error.value = ''; errors.value = {}; busy.value = true
  try {
    if (kind.value === 'aviso') await managementApi.notice({ ...notice, submission_key: key })
    else await managementApi.create({ ...fields.value, demand_type: kind.value, contributor_id: contributor.value, submission_key: key }, files.value)
    emit('saved'); visible.value = false
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Não foi possível cadastrar.'
    // Mantém o mesmo cadastro/chave em nova tentativa após resultado incerto.
    if (err instanceof ApiError && err.status === 422) errors.value = validationMessages(err.detail,
      ['title', 'description', 'responsible_id', 'assumptions', 'current_problems', 'expected_benefits', 'files'])
    uncertain.value = err instanceof ApiError && (err.status === 0 || err.status >= 500 || (err.status >= 200 && err.status < 300))
  } finally { busy.value = false }
}
</script>
<template>
  <AppDialog id="management-create" :visible="visible" title="Nova demanda ou aviso" icon="pi pi-plus" :busy="busy" @update:visible="visible = false" @closed="emit('closed')">
    <form id="management-create-form" class="space-y-5" @submit.prevent="submit">
      <FormField id="management-kind" label="Tipo *">
        <Select v-model="kind" input-id="management-kind" :options="[...demandTypes, { label: 'Aviso', value: 'aviso' }]" option-label="label" option-value="value"
          placeholder="Selecione para continuar" :disabled="busy || uncertain" class="w-full" />
      </FormField>
      <template v-if="kind === 'aviso'">
        <FormField id="notice-title" v-slot="{ controlProps }" label="Título *"><InputText v-bind="controlProps" v-model="notice.title" :maxlength="250" :disabled="busy || uncertain" class="w-full" required /></FormField>
        <FormField id="notice-description" v-slot="{ controlProps }" label="Descrição *"><Textarea v-bind="controlProps" v-model="notice.description" :maxlength="4000" :rows="4" :disabled="busy || uncertain" class="w-full" required /></FormField>
        <div class="grid gap-4 sm:grid-cols-2">
          <DemandDateField id="notice-start" v-model="notice.starts_at" label="Início (opcional)" time :disabled="busy || uncertain" />
          <DemandDateField id="notice-end" v-model="notice.ends_at" label="Fim (opcional)" time :disabled="busy || uncertain" />
        </div>
        <label class="flex items-center gap-2 text-sm"><Checkbox v-model="notice.hide_after_end" binary :disabled="busy || uncertain" />Finalizar automaticamente após o fim</label>
      </template>
      <template v-else-if="kind">
        <ManagementEditor v-model="fields" :kind="kind" :options="options" :errors="errors" :disabled="busy || uncertain" />
        <FormField v-if="kind !== 'atividade'" id="internal-contributor" label="Contribuinte (opcional)">
          <Select v-model="contributor" input-id="internal-contributor" :options="options.contributors" option-label="name" option-value="id" filter show-clear :disabled="busy || uncertain" class="w-full" />
        </FormField>
        <label class="block text-sm">{{ kind === 'atividade' ? 'Anexos (opcional)' : 'Documentos ou evidências *' }}
          <input type="file" multiple :accept="fileAccept" :disabled="busy || uncertain" class="mt-2 block w-full text-sm" @change="files = Array.from(($event.target as HTMLInputElement).files ?? [])" />
        </label>
        <p class="text-xs text-dj-muted">Até 10 arquivos, 10 MB por arquivo e 40 MB no total.</p>
        <Message v-if="errors.files" severity="error">{{ errors.files }}</Message>
      </template>
      <Message v-if="error" severity="error" role="alert">{{ error }}</Message>
      <Message v-if="uncertain" severity="warn">Confira o painel antes de iniciar outro cadastro. Se necessário, repita este envio com os mesmos dados.</Message>
    </form>
    <template #footer>
      <SecondaryButton type="button" label="Voltar" outlined :disabled="busy" @click="visible = false" />
      <Button type="submit" form="management-create-form" label="Cadastrar" :loading="busy" :disabled="busy || !kind" />
    </template>
  </AppDialog>
</template>
