import { useAppDispatch, useAppSelector } from "@/app/hooks";
import EditingForm from "@/components/EditingForm";
import { deleteCommercial } from "@/data/dataSlice";
import { activateEdit } from "@/data/editModal";
import { CommercialData } from "@/types";
import { DeleteOutlined, EditOutlined } from "@ant-design/icons";
import {
  Button,
  Checkbox,
  CheckboxProps,
  ConfigProvider,
  Descriptions,
  DescriptionsProps,
  Flex,
  Input,
  Modal,
  Space,
  Table,
  TableProps,
  Typography,
} from "antd";
import { OTPProps } from "antd/es/input/OTP";
import { useState } from "react";

const Step3 = () => {
  const [open, setOpen] = useState<boolean>(false);
  const [checked, setChecked] = useState<boolean>(false);
  const dataState = useAppSelector((state) => state.dataReducer);
  const editState = useAppSelector(state => state.editReducer);
  const c = dataState.commercial_register[0];
  const dispatch = useAppDispatch();
  const commission = useAppSelector(
    (state) => state.commissionReducer.commission
  );

  const items: DescriptionsProps["items"] = [
    {
      label: "Company",
      span: "filled",
      children: dataState.company,
    },
    {
      label: "Commercial Register",
      span: "filled",
      children: dataState.tax_id,
    },
    {
      label: "Company in Arabic",
      span: "filled",
      children: dataState.company_name_in_arabic,
    },
    //@ts-ignore
    // ...dataState.commercial_register((c) => [
    //   {
    //     label: "Commercial Name",
    //     children: c.commercial_register_name,
    //   },
    //   {
    //     label: "Commercial Number",
    //     span: 'filled',
    //     children: c.commercial_register_number,
    //   },
    //   {
    //     label: "Commercial Info",
    //     span: 'filled',
    //     children: (
    //       <>
    //         Short Address: {c.short_address}
    //         <br />
    //         Building Number: {c.building_no}
    //         <br />
    //         Street: {c.address_line1}
    //         <br />
    //         Secondary No: {c.address_line2}
    //         <br />
    //         City: {c.city}
    //         <br />
    //         District: {c.district}
    //         <br />
    //         Postal Code: {c.pincode}
    //         <br />
    //         {c.more_info ?
    //         `More Info: ${c.more_info}`
    //       : null
    //       }
    //       </>
    //     ),
    //   },
    // ]),
    {
      label: "Commercial Name",
      children: c.commercial_register_name,
    },
    {
      label: "Commercial Number",
      span: "filled",
      children: c.commercial_register_number,
    },
    {
      label: "Commercial Info",
      span: "filled",
      children: (
        <>
          Short Address: {c.short_address}
          <br />
          Building Number: {c.building_no}
          <br />
          Street: {c.address_line1}
          <br />
          Secondary No: {c.address_line2}
          <br />
          City: {c.city}
          <br />
          District: {c.district}
          <br />
          Postal Code: {c.pincode}
          <br />
          {c.more_info ? `More Info: ${c.more_info}` : null}
        </>
      ),
    },
  ];

  const columns: TableProps<CommercialData>["columns"] = [
    {
      title: "Commercial Name",
      dataIndex: "commercial_register_name",
      key: "commercial_register_name",
    },
    {
      title: "Commercial Number",
      dataIndex: "commercial_register_number",
      key: "commercial_register_number",
    },
    {
      title: "Short Address",
      dataIndex: "short_address",
      key: "short_address",
    },
    {
      title: "Building Number",
      dataIndex: "building_no",
      key: "building_no",
    },
    {
      title: "Street",
      dataIndex: "address_line1",
      key: "address_line1",
    },
    {
      title: "Secondary No",
      dataIndex: "address_line2",
      key: "address_line2",
    },
    {
      title: "City",
      dataIndex: "city",
      key: "city",
    },
    {
      title: "District",
      dataIndex: "district",
      key: "district",
    },
    {
      title: "Postal Code",
      dataIndex: "pincode",
      key: "pincode",
    },
    ...(!checked
      ? [
          {
            title: "Action",
            key: "action",
            render: (_: unknown, record: CommercialData) => (
              <Space size="middle">
                <EditOutlined
                  onClick={() => handleEditCommercial(record)}
                  className="cursor-pointer text-lg hover:text-blue-300"
                />
                <DeleteOutlined
                  onClick={() => {
                    dispatch(deleteCommercial(record));
                    if (!dataState.commercial_register.length) {
                      location.reload();
                    }
                  }}
                  className="cursor-pointer text-lg hover:text-red-500"
                />
              </Space>
            ),
          },
        ]
      : []),
  ];

  const onChange: CheckboxProps["onChange"] = (e) => {
    setChecked(e.target.checked);
  };

  const handleEditCommercial = (record: CommercialData) => {
    dispatch(activateEdit({ commercial: record }));
  };

  const onOTPChange: OTPProps["onChange"] = (text) => {
    console.log("onChange:", text);
  };

  const onInput: OTPProps["onInput"] = (value) => {
    console.log("onInput:", value);
  };

  const sharedProps: OTPProps = {
    onChange: onOTPChange,
    onInput,
  };
  return (
    <Flex vertical className="w-full p-5">
      {commission === "main" ? (
        <Descriptions
          className="bg-[#ffffff00] rounded p-5"
          bordered
          title="Company Information"
          items={items}
        />
      ) : (
        <ConfigProvider
          theme={{
            components: {
              Table: {
                headerBg: "#483f61",
                headerColor: "#ffffff",
              },
            },
          }}
        >
          <Table<CommercialData>
            columns={columns}
            dataSource={dataState.commercial_register}
          />
        </ConfigProvider>
      )}
      <Flex justify="space-between" align="center" className="mt-auto">
        <Checkbox className="text-lg" onChange={onChange} value={checked}>
          By checkign this box i fully acknowledge that this data is correct and
          any errors is on my resposiblity
        </Checkbox>
        <Button
          onClick={() => setOpen(true)}
          disabled={!checked}
          size="large"
          className="bg-[#483f61] text-white w-1/12 disabled:opacity-85"
        >
          OTP
        </Button>
      </Flex>
      <Modal
        centered
        title="Please provide an OTP"
        open={open}
        onOk={() => console.log("object")}
        onCancel={() => setOpen(false)}
      >
        <Flex gap="middle" align="center" vertical className="p-5">
          {dataState.commercial_register.map((com,index) => (
            <>
            <Typography.Text className="text-lg">{com.commercial_register_name}</Typography.Text>
          <Input.OTP key={index} formatter={(str) => str.toUpperCase()} {...sharedProps} />
            </>
          ))}
        </Flex>
      </Modal>
      {editState.edit && <EditingForm />}
    </Flex>
  );
};

export default Step3;
