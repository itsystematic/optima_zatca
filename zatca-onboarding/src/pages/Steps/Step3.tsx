import { useAppDispatch, useAppSelector } from "@/app/hooks";
import EditingForm from "@/components/EditingForm";
import OTPModal from "@/components/OTPModal";
import { step3Tour } from "@/constants";
import { deleteCommercial } from "@/data/dataSlice";
import { activateEdit } from "@/data/editModal";
import { setTourSteps } from "@/data/tour";
import { CommercialData } from "@/types";
import { DeleteOutlined, EditOutlined } from "@ant-design/icons";
import {
  Button,
  Checkbox,
  CheckboxProps,
  Flex,
  Space,
  Table,
  TableProps,
} from "antd";
import { useEffect, useState } from "react";

const Step3 = () => {
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState<boolean>(false);
  const [checked, setChecked] = useState<boolean>(false);
  const dataState = useAppSelector((state) => state.dataReducer);
  const editState = useAppSelector((state) => state.editReducer);
  const currentPage = useAppSelector((state) => state.pageReducer.currentPage);
  const [isLaptop, setLapTop] =  useState<boolean>(false);

  const columns: TableProps<CommercialData>["columns"] = [
    {
      title: "Commercial Register",
      children: [
        {
          title: __("Commercial Name"),
          dataIndex: "commercial_register_name",
          key: "commercial_register_name",
        },
        {
          title: __("Commercial Number"),
          dataIndex: "commercial_register_number",
          key: "commercial_register_number",
          width: "50px",
        },
      ],
    },
    {
      title: "Address",
      children: [
        {
          title: __("City"),
          dataIndex: "city",
          key: "city",
        },
        {
          title: __("Short Address"),
          dataIndex: "short_address",
          key: "short_address",
        },
        {
          title: __("Street"),
          dataIndex: "address_line1",
          key: "address_line1",
        },
        {
          title: __("Block"),
          children: [
            {
              title: __("Building No"),
              dataIndex: "building_no",
              key: "building_no",
              width: "20px",
            },
            {
              title: __("District"),
              dataIndex: "district",
              key: "district",
            },
          ],
        },
        {
          title: __("Secondary No"),
          dataIndex: "address_line2",
          key: "address_line2",
        },
      ],
    },
    {
      title: __("Postal Code"),
      dataIndex: "pincode",
      key: "pincode",
      width: "20px",
    },
    {
      title: __("Action"),
      width: 100,
      key: "action",
      fixed: 'right',
      render: (_: unknown, record: CommercialData) => !checked ? (
        <Space size="middle" id="actions">
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
      ): null,
    },
  ];

  const onChange: CheckboxProps["onChange"] = (e) => {
    setChecked(e.target.checked);
  };

  const handleEditCommercial = (record: CommercialData) => {
    dispatch(activateEdit({ commercial: record }));
  };

  useEffect(() => {
    if (!dataState.commercial_register.length && currentPage === 4)
      location.reload();
  }, [dataState.commercial_register.length]);

  useEffect(() => {
    dispatch(setTourSteps(step3Tour));
  }, []);

  useEffect(() => {

    console.log(innerWidth);
      if (1366 < innerWidth && innerWidth < 1600) {
      setLapTop(true);
      return
    }
    setLapTop(false);
  } , [innerWidth])
  return (
    <>
      <Flex vertical className="w-full p-5 laptop:p-2 h-full overflow-y-auto">
        <Table<CommercialData>
          columns={columns}
          id="branches_table"
          pagination={
            dataState.commercial_register.length > (isLaptop ? 4 : 5) ? { pageSize: isLaptop ? 4 : 5 } : false
          }
          dataSource={
            dataState.commercial_register.filter((c) => !c.phase) || []
          }
          bordered
        />

        <Flex
          className="mt-auto"
          justify="space-between"
          align="center"
          id="otp_check"
        >
          <Checkbox className="text-lg text-[#483f61] font-light" onChange={onChange} checked={checked}>
            {__(
              "By Checking This Box I Fully Acknowledge This Data Is Correct And Any Errors Is On My Responsibility"
            )}
          </Checkbox>
          <Button
            onClick={() => setOpen(true)}
            disabled={!checked}
            size="large"
            className={`bg-[#483f61] text-white w-1/12 disabled:opacity-10`}
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
