import { useAppDispatch, useAppSelector } from "@/app/hooks";
import EditingForm from "@/components/EditingForm";
import OTPModal from "@/components/OTPModal";
import { deleteCommercial } from "@/data/dataSlice";
import { activateEdit } from "@/data/editModal";
import { CommercialData } from "@/types";
import { DeleteOutlined, EditOutlined } from "@ant-design/icons";
import {
  Button,
  Checkbox,
  CheckboxProps,
  ConfigProvider,
  Flex,
  Space,
  Table,
  TableProps
} from "antd";
import { useEffect, useState } from "react";

const Step3 = () => {
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState<boolean>(false);
  const [checked, setChecked] = useState<boolean>(false);
  const dataState = useAppSelector((state) => state.dataReducer);
  const editState = useAppSelector((state) => state.editReducer);

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





  useEffect(() => {
    if (!dataState.commercial_register.length) location.reload()

  }, [dataState.commercial_register.length])

  return (
    <>
      <Flex vertical className="w-full p-5">
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
            pagination={false}
            dataSource={dataState.commercial_register || []}
          />
        </ConfigProvider>
        <Flex justify="space-between" align="center" className="mt-auto">
          <Checkbox className="text-lg" onChange={onChange} checked={checked}>
            By checkign this box i fully acknowledge that this data is correct
            and any errors is on my resposiblity
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
          <OTPModal open={open} setOpen={setOpen} />
        {editState.edit && <EditingForm />}
      </Flex>
    </>
  );
};

export default Step3;
