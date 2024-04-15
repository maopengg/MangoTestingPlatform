<template>
  <!-- support from v2.25.0  -->
  <a-table :columns="columns" :data="data">
    <template #name="{ record, rowIndex }">
      <a-input v-model="record.name" />
    </template>
  </a-table>
</template>

<script>
  import { reactive } from 'vue'

  export default {
    setup() {
      const columns = [
        {
          title: 'name',
          dataIndex: 'name',
          slotName: 'name',
        },
        {
          title: 'Salary',
          dataIndex: 'salary',
        },
      ]

      const data = reactive([
        {
          key1: '1',
          name: 'Jane Doe',
          salary: 23000,
          address: '32 Park Road, London',
          province: 'Beijing',
          city: 'Haidian',
          email: 'jane.doe@example.com',
        },
        {
          key1: '2',
          name: 'Alisa Ross',
          salary: 25000,
          address: '35 Park Road, London',
          email: 'alisa.ross@example.com',
        },
      ])
      return {
        columns,
        data,
      }
    },
  }
</script>
