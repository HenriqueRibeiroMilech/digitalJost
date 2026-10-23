<script setup lang="ts">
import { computed } from 'vue'
import FormField from '@/shared/components/FormField.vue'
import DatePicker from '@/volt/DatePicker.vue'
import { dateValue } from '../managementTypes'
const props = defineProps<{ id: string; label: string; error?: string; disabled?: boolean; time?: boolean }>()
const model = defineModel<string | null>({ required: true })
const date = computed({
  get: () => model.value ? new Date(model.value.length === 10 ? model.value + 'T12:00:00' : model.value) : null,
  set: (value: Date | null) => {
    model.value = value ? dateValue(value) + (props.time ? `T${String(value.getHours()).padStart(2, '0')}:${String(value.getMinutes()).padStart(2, '0')}:00` : '') : null
  },
})
</script>
<template>
  <FormField :id="id" v-slot="{ controlProps }" :label="label" :error="error">
    <DatePicker v-model="date" :input-id="id" :invalid="controlProps.invalid" :disabled="disabled"
      :input-props="{ 'aria-describedby': controlProps['aria-describedby'], 'aria-invalid': controlProps['aria-invalid'] }"
      date-format="dd/mm/yy" :show-time="time" hour-format="24" show-icon show-button-bar fluid :manual-input="false" />
  </FormField>
</template>
