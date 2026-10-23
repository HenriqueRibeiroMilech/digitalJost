<script setup lang="ts">
import FormField from '@/shared/components/FormField.vue'
import InputText from '@/volt/InputText.vue'
import Textarea from '@/volt/Textarea.vue'
import Select from '@/volt/Select.vue'
import InputNumber from '@/volt/InputNumber.vue'
import type { DemandType, ManagementFields, ManagementOptions } from '../managementTypes'
defineProps<{ kind: DemandType; options: ManagementOptions; disabled?: boolean; errors?: Record<string, string> }>()
const fields = defineModel<ManagementFields>({ required: true })
const details = [{ key: 'assumptions', label: 'Premissas' }, { key: 'current_problems', label: 'Problemas atuais' }, { key: 'expected_benefits', label: 'Ganhos esperados' }] as const
const hours = [{ key: 'estimated_hours', label: 'Tempo estimado (h)' }, { key: 'daily_hours', label: 'Tempo diário (h)' }, { key: 'completed_hours', label: 'Tempo realizado (h)' }] as const
</script>
<template>
  <div class="space-y-4">
    <FormField id="management-demand-title" v-slot="{ controlProps }" label="Título *" :error="errors?.title">
      <InputText v-bind="controlProps" v-model="fields.title" :maxlength="250" :disabled="disabled" required class="w-full" />
    </FormField>
    <FormField id="management-description" v-slot="{ controlProps }" label="Objetivo ou descrição *" :error="errors?.description">
      <Textarea v-bind="controlProps" v-model="fields.description" :rows="4" :maxlength="4000" :disabled="disabled" required class="w-full" />
    </FormField>
    <div class="grid gap-4 sm:grid-cols-2">
      <FormField id="management-responsible" label="Responsável *" :error="errors?.responsible_id">
        <Select v-model="fields.responsible_id" input-id="management-responsible" :options="options.responsibles" option-label="name" option-value="id"
          filter placeholder="Selecione" :disabled="disabled" class="w-full" :invalid="!!errors?.responsible_id" pt:label:aria-required="true" />
      </FormField>
      <FormField id="management-urgency" label="Urgência">
        <Select v-model="fields.urgency" input-id="management-urgency" :options="['Alta', 'Média', 'Baixa']" :disabled="disabled" class="w-full" />
      </FormField>
    </div>
    <div v-if="kind === 'projeto' || kind === 'melhoria'" class="grid gap-4 lg:grid-cols-3">
      <FormField v-for="item in details" :id="'management-' + item.key" :key="item.key" v-slot="{ controlProps }" :label="item.label + ' *'" :error="errors?.[item.key]">
        <Textarea v-bind="controlProps" v-model="fields[item.key]" :rows="4" :maxlength="4000" :disabled="disabled" required class="w-full" />
      </FormField>
    </div>
    <div class="grid gap-4 sm:grid-cols-3">
      <FormField v-for="item in hours" :id="'management-' + item.key" :key="item.key" :label="item.label" :error="errors?.[item.key]">
        <InputNumber v-model="fields[item.key]" :input-id="'management-' + item.key" :min="0" :max="99999.99" :max-fraction-digits="2" locale="pt-BR" :disabled="disabled" fluid />
      </FormField>
      <FormField id="management-difficulty" label="Dificuldade">
        <Select v-model="fields.difficulty" input-id="management-difficulty" :options="['Baixa', 'Média', 'Alta']" show-clear :disabled="disabled" class="w-full" />
      </FormField>
      <FormField id="management-priority" label="Prioridade (1 a 10)" :error="errors?.priority">
        <InputNumber v-model="fields.priority" input-id="management-priority" :min="1" :max="10" :max-fraction-digits="0" :disabled="disabled" fluid />
      </FormField>
    </div>
    <FormField id="management-observations" v-slot="{ controlProps }" label="Observações" :error="errors?.observations">
      <Textarea v-bind="controlProps" v-model="fields.observations" :rows="4" :maxlength="4000" :disabled="disabled" class="w-full" />
    </FormField>
  </div>
</template>
