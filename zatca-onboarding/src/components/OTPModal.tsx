import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { setCurrentPage } from "@/data/currentPage";
import { addOTP } from "@/data/dataSlice";
import { CommercialData } from "@/types";
import { Flex, Input, message, Modal, Typography } from "antd";
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
      if (isDev) {
        dispatch(setCurrentPage(204));
        return
      }
      setOtpLoading(true);
      dispatch(addOTP(otpValues));
      const data = await frappe.call({
        method: "optima_zatca.zatca.api.register_company",
        args: dataState,
      });

      if (data) {
        setOtpLoading(false);
        dispatch(setCurrentPage(200));
      }
    } catch (err: any) {
      setOtpLoading(false);
      messageApi.error({
        type: "error",
        content: err.message ? err.message : err,
      });
    }
  };

  return (
    <>
      {contextHolder}
      <Modal
        centered
        title={__("Please provide an OTP")}
        open={open}
        onOk={() => handleSubmit(otpValues)}
        confirmLoading={otpLoading}
        onCancel={() => setOpen(false)}
        className="w-[35%]"
        okText={__("Confirm")}
        cancelText={__("Cancel")}
        okButtonProps={{
          className: 'bg-[#39b54a] text-white disabled:opacity-50',
          disabled:
            Object.keys(otpValues).length <
            dataState.commercial_register.length,
        }}
      >
        <Flex gap="middle" align="center" vertical className="p-5">
          {dataState.commercial_register.map((com, index) => (
            <Flex
              key={index}
              align="center"
              justify="space-between"
              className="w-full"
            >
              {!com.otp ? (
                <>
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
                </>
              ) : null}
            </Flex>
          ))}
        </Flex>
      </Modal>
    </>
  );
};

export default OTPModal;
