<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import AppDialog from '@/shared/components/AppDialog.vue'
import FormField from '@/shared/components/FormField.vue'
import Button from '@/volt/Button.vue'
import SecondaryButton from '@/volt/SecondaryButton.vue'
import Select from '@/volt/Select.vue'
import Textarea from '@/volt/Textarea.vue'
import Message from '@/volt/Message.vue'
import DemandDateField from './DemandDateField.vue'
import { managementApi } from '../managementApi'
import type { ManagedDetail, ManagementOptions } from '../managementTypes'
import { dayLabel } from '../managementTypes'
import { ApiError } from '@/shared/api/client'
import { validationMessages } from '@/shared/api/validation'
const props = defineProps<{ demand: ManagedDetail; action: string; options: ManagementOptions }>()
const emit = defineEmits<{ saved: [value: ManagedDetail]; closed: []; busy: [value: boolean] }>()
const titles: Record<string, string> = { accept: 'Aceitar solicitação', decline: 'Recusar solicitação', review_information: 'Solicitar informações ou reunião',
  start: 'Iniciar demanda', complete: 'Concluir demanda', cancel: 'Cancelar demanda', schedule: 'Agendar início', unschedule: 'Cancelar agendamento',
  information: 'Solicitar informações ou reunião', validate: 'Iniciar validação', pause: 'Pausar demanda', third_party: 'Aguardar terceiros', resume: 'Retomar demanda', deadline: 'Alterar prazo' }
const busy = ref(false); const visible = ref(true); const error = ref(''); const errors = ref<Record<string, string>>({})
watch(busy, value => emit('busy', value), { flush: 'sync' })
const fields = reactive({ reason: '', responsible_id: props.options.current_user_id, classification: 'melhoria', information_kind: 'informacoes',
  initial_deadline: null as string | null, scheduled_start_date: null as string | null, expected_return: null as string | null,
  deadline: props.demand.deadline })
const information = computed(() => ['information', 'review_information'].includes(props.action))
const needsReason = computed(() => ['decline', 'cancel', 'pause', 'third_party', 'deadline'].includes(props.action) || information.value)
async function submit() {
  if (busy.value) return
  error.value = ''; errors.value = {}; busy.value = true
  try {
    const payload: Record<string, unknown> = { row_version: props.demand.row_version }
    let saved: ManagedDetail
    if (props.action === 'deadline') {
      saved = await managementApi.deadline(props.demand.id, { ...payload, deadline: fields.deadline, reason: fields.reason })
    } else if (['accept', 'decline', 'review_information'].includes(props.action)) {
      payload.action = props.action === 'review_information' ? 'information' : props.action
      if (props.action === 'accept') {
        payload.responsible_id = fields.responsible_id
        payload.classification = props.demand.entry_kind === 'erro' ? null : fields.classification
      } else { payload.reason = fields.reason; payload.information_kind = fields.information_kind }
      saved = await managementApi.review(props.demand.id, payload)
    } else {
      payload.action = props.action
      if (needsReason.value || fields.reason) payload.reason = fields.reason
      if (information.value) payload.information_kind = fields.information_kind
      if (['pause', 'third_party'].includes(props.action)) payload.expected_return = fields.expected_return
      if (props.action === 'schedule') payload.scheduled_start_date = fields.scheduled_start_date
      if (['start', 'schedule'].includes(props.action) && !props.demand.deadline) payload.initial_deadline = fields.initial_deadline
      saved = await managementApi.action(props.demand.id, payload)
    }
    emit('saved', saved); visible.value = false
  } catch (err) {
    if (err instanceof ApiError) errors.value = validationMessages(err.detail, ['reason', 'responsible_id', 'classification', 'initial_deadline', 'deadline', 'scheduled_start_date', 'expected_return'])
    error.value = err instanceof Error ? err.message : 'Não foi possível concluir a ação.'
  } finally { busy.value = false }
}
</script>
<template>
  <AppDialog id="management-action" :visible="visible" :title="titles[action] ?? 'Atualizar demanda'" :subtitle="demand.title" :busy="busy" icon="pi pi-directions"
    @update:visible="visible = false" @closed="emit('closed')">
    <form id="management-action-form" class="space-y-4" @submit.prevent="submit">
      <p class="text-sm text-dj-muted">{{ titles[action] }} · #{{ demand.id }}</p>
      <template v-if="action === 'accept'">
        <FormField id="review-responsible" label="Responsável *" :error="errors.responsible_id">
          <Select v-model="fields.responsible_id" input-id="review-responsible" :options="options.responsibles" option-label="name" option-value="id" filter :disabled="busy" class="w-full" />
        </FormField>
        <FormField v-if="demand.entry_kind !== 'erro'" id="review-classification" label="Tipo da demanda *" :error="errors.classification">
          <Select v-model="fields.classification" input-id="review-classification" :options="[{ label: 'Melhoria', value: 'melhoria' }, { label: 'Projeto', value: 'projeto' }]" option-label="label" option-value="value" :disabled="busy" class="w-full" />
        </FormField>
        <p v-else class="text-sm">O relato será tratado como Erro.</p>
      </template>
      <FormField v-if="information" id="information-kind" label="O que deseja solicitar?">
        <Select v-model="fields.information_kind" input-id="information-kind" :options="[{ label: 'Mais informações', value: 'informacoes' }, { label: 'Agendamento de reunião', value: 'reuniao' }]" option-label="label" option-value="value" :disabled="busy" class="w-full" />
      </FormField>
      <DemandDateField v-if="action === 'schedule'" id="scheduled-start" v-model="fields.scheduled_start_date" label="Data de início *" :error="errors.scheduled_start_date" :disabled="busy" />
      <template v-if="['start', 'schedule'].includes(action)">
        <DemandDateField v-if="!demand.deadline" id="initial-deadline" v-model="fields.initial_deadline"
          :label="demand.demand_type === 'atividade' ? 'Prazo inicial (opcional)' : 'Prazo inicial *'" :error="errors.initial_deadline" :disabled="busy" />
        <p v-else class="rounded-xl bg-dj-canvas p-3 text-sm">Prazo já definido: {{ dayLabel(demand.deadline) }}</p>
      </template>
      <DemandDateField v-if="action === 'deadline'" id="new-deadline" v-model="fields.deadline" label="Novo prazo *" :error="errors.deadline" :disabled="busy" />
      <DemandDateField v-if="['pause', 'third_party'].includes(action)" id="expected-return" v-model="fields.expected_return"
        :label="action === 'pause' ? 'Previsão de retorno *' : 'Previsão de retorno (opcional)'" :error="errors.expected_return" :disabled="busy" />
      <FormField v-if="needsReason || action === 'complete'" id="action-reason" v-slot="{ controlProps }"
        :label="information ? 'Descreva as informações necessárias ou o objetivo da reunião *' : needsReason ? 'Justificativa *' : 'Resumo da conclusão (opcional)'" :error="errors.reason">
        <Textarea v-bind="controlProps" v-model="fields.reason" :rows="4" :maxlength="4000" :disabled="busy" class="w-full" />
      </FormField>
      <Message v-if="error" severity="error" role="alert">{{ error }}</Message>
    </form>
    <template #footer>
      <SecondaryButton type="button" label="Voltar" outlined :disabled="busy" @click="visible = false" />
      <Button type="submit" form="management-action-form" label="Confirmar" :loading="busy" :disabled="busy" />
    </template>
  </AppDialog>
</template>
