import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { setCurrentPage } from "@/data/currentPage";
import { addOTP } from "@/data/dataSlice";
import { CommercialData } from "@/types";
import { ConfigProvider, Flex, Input, message, Modal, Typography } from "antd";
import React, { useState } from "react";

interface Props {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

const OTPModal: React.FC<Props> = ({ open, setOpen }) => {
  const dispatch = useAppDispatch();
  const dataState = useAppSelector((state) => state.dataReducer);

  const [otpValues, setOtpValues] = useState({});
  const [otpLoading, setOtpLoading] = useState<boolean>(false);
  const [messageApi, contextHolder] = message.useMessage();


  const handleOtpChange = (value: string, commercial: CommercialData) => {
    setOtpValues((prev) => ({
      ...prev,
      [commercial.commercial_register_number]: value,
    }));
  };

  const handleSubmit = async (otpValues: any) => {
    try {
      setOtpLoading(true);

      dispatch(addOTP(otpValues));
      const data = await frappe.call({
        method: "optima_zatca.zatca.api.register_company_phase_two",
        args: dataState,
      });

      if (data) {
        setOtpLoading(false);
        dispatch(setCurrentPage(200));
      }
    } catch (err: any) {
      messageApi.error({
        type: "error",
        content: err.message ? err.message : err,
      });
    }
  };
  return (
    <>
    <ConfigProvider
    theme={{
        components: {
            Modal: {
                contentBg: '#f3f3f3',
                headerBg: '#f3f3f3',
            }
        }
    }}>
    {contextHolder}
    <Modal
      centered
      title="Please provide an OTP"
      open={open}
      onOk={() => handleSubmit(otpValues)}
      confirmLoading={otpLoading}
      onCancel={() => setOpen(false)}
      className="w-[35%]"
    >
      <Flex gap="middle" align="center" vertical className="p-5">
        {dataState.commercial_register.map((com, index) => (
          <Flex
            key={index}
            align="center"
            justify="space-between"
            className="w-full"
          >
            <Typography.Text className="text-lg">
              {com.commercial_register_name}
            </Typography.Text>
            <div>
              <Input.OTP
                key={index}
                formatter={(str) => str.toUpperCase()}
                onChange={(e) => handleOtpChange(e, com)}
              />
            </div>
          </Flex>
        ))}
      </Flex>
    </Modal>
    </ConfigProvider>
    </>

  );
};

export default OTPModal;
